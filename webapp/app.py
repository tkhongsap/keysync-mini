"""Flask web application for interacting with KeySync Mini."""

from __future__ import annotations

import io
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict

from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)

BASE_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = BASE_DIR / 'src'
if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))

from src.logger import setup_logging
from src.keysync import run_reconciliation

SCENARIOS = ['normal', 'drift', 'failure', 'recovery']
MODES = ['full', 'incremental']


def create_app() -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)

    secret_key = os.environ.get('KEYSYNC_SECRET_KEY', 'keysync-mini-demo')
    app.config['SECRET_KEY'] = secret_key

    output_dir = Path(os.environ.get('KEYSYNC_OUTPUT_DIR', 'output')).resolve()
    app.config['OUTPUT_DIR'] = output_dir
    app.config['LAST_RUN'] = None

    log_level = os.environ.get('KEYSYNC_LOG_LEVEL', 'INFO')
    log_file = os.environ.get('KEYSYNC_WEB_LOG', 'logs/keysync_web.log')
    setup_logging(log_level=log_level, log_file=log_file)

    @app.route('/', methods=['GET', 'POST'])
    def index():
        """Render the dashboard and handle reconciliation requests."""
        default_config = os.environ.get('KEYSYNC_CONFIG_PATH', 'keysync-config.yaml')
        default_output = app.config['OUTPUT_DIR']

        if request.method == 'POST':
            form = request.form
            config_path = (form.get('config_path') or default_config).strip() or default_config
            mode = form.get('mode', 'full')
            scenario = form.get('scenario', 'normal')
            generate_data = form.get('generate_data') == 'on'
            dry_run = form.get('dry_run') == 'on'
            auto_approve = form.get('auto_approve') == 'on'
            verbose = form.get('verbose') == 'on'
            output_directory_raw = (form.get('output_dir') or str(default_output)).strip()
            output_directory = output_directory_raw or str(default_output)

            try:
                keys = int(form.get('keys') or 1000)
            except ValueError:
                flash('Keys per system must be an integer.', 'error')
                return redirect(url_for('index'))

            seed_raw = form.get('seed')
            try:
                seed = int(seed_raw) if seed_raw else None
            except ValueError:
                flash('Seed must be an integer.', 'error')
                return redirect(url_for('index'))

            if mode not in MODES:
                flash('Invalid reconciliation mode selected.', 'error')
                return redirect(url_for('index'))

            if scenario not in SCENARIOS:
                flash('Invalid scenario selected.', 'error')
                return redirect(url_for('index'))

            log_buffer = io.StringIO()
            handler = logging.StreamHandler(log_buffer)
            handler.setLevel(logging.DEBUG if verbose else logging.INFO)
            handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

            root_logger = logging.getLogger()
            original_level = root_logger.level
            if verbose and original_level > logging.DEBUG:
                root_logger.setLevel(logging.DEBUG)

            root_logger.addHandler(handler)

            try:
                run_details = run_reconciliation(
                    config=config_path,
                    mode=mode,
                    dry_run=dry_run,
                    auto_approve=auto_approve,
                    generate_data=generate_data,
                    scenario=scenario,
                    keys=keys,
                    seed=seed,
                    output_dir=output_directory,
                )
                status = 'success'
                flash(f"Reconciliation run {run_details['run_id']} completed successfully.", 'success')
            except Exception as exc:  # pylint: disable=broad-except
                run_details = {
                    'status': 'error',
                    'error': str(exc),
                }
                status = 'error'
                flash(f'Reconciliation failed: {exc}', 'error')
            finally:
                root_logger.removeHandler(handler)
                root_logger.setLevel(original_level)

            run_details['mode'] = run_details.get('mode', mode)
            run_details['scenario'] = scenario
            run_details['dry_run'] = dry_run
            run_details['auto_approve'] = auto_approve
            run_details['generate_data'] = generate_data
            run_details['keys'] = keys
            run_details['seed'] = seed
            run_details['logs'] = log_buffer.getvalue()
            run_details['verbose'] = verbose
            run_details['output_dir'] = output_directory
            run_details['config_path'] = config_path
            run_details['report_files'] = [
                Path(path).name for path in run_details.get('reports', []) if path
            ]
            if run_details.get('json_report'):
                run_details['json_report_name'] = Path(run_details['json_report']).name
            else:
                run_details['json_report_name'] = None
            run_details['view'] = build_view_model(run_details)
            run_details['status'] = status

            app.config['LAST_RUN'] = run_details
            app.config['OUTPUT_DIR'] = Path(output_directory).resolve()

            return redirect(url_for('index'))

        last_run = app.config.get('LAST_RUN')

        return render_template(
            'index.html',
            scenarios=SCENARIOS,
            modes=MODES,
            default_config=default_config,
            default_output=str(default_output),
            last_run=last_run,
        )

    @app.route('/reports/<path:filename>')
    def download_report(filename: str):
        """Serve generated report files from the output directory."""
        output_path = app.config.get('OUTPUT_DIR', Path('output')).resolve()
        target = output_path / filename
        if not target.exists() or not target.is_file():
            abort(404)
        return send_from_directory(output_path, filename, as_attachment=True)

    return app


def build_view_model(run_details: Dict[str, Any]) -> Dict[str, Any]:
    """Prepare reconciliation results for display in templates."""
    results = run_details.get('results') or {}
    comparison = results.get('comparison') or {}
    stats = comparison.get('statistics') or {}
    discrepancies = results.get('discrepancies') or {}
    provisioning = results.get('provisioning') or []

    system_counts = stats.get('system_counts') or {}
    discrepancy_summary = discrepancies.get('summary') or {}
    propagation_gaps = discrepancies.get('propagation_gaps') or {}
    out_of_authority = discrepancies.get('out_of_authority_keys') or {}
    duplicate_keys = discrepancies.get('duplicate_keys') or {}

    keys_only_in_a = comparison.get('comparison', {}).get('keys_only_in_a') if isinstance(comparison.get('comparison'), dict) else comparison.get('keys_only_in_a')
    keys_missing_in_a = comparison.get('comparison', {}).get('keys_missing_in_a') if isinstance(comparison.get('comparison'), dict) else comparison.get('keys_missing_in_a')

    def sorted_list(values: Any) -> list[Any]:
        if values is None:
            return []
        if isinstance(values, set):
            return sorted(values)
        if isinstance(values, list):
            return sorted(values)
        return list(values)

    view = {
        'stats_items': [
            ('Total Unique Keys', stats.get('total_unique_keys', 0)),
            ('Keys in System A', stats.get('keys_in_a', 0)),
            ('Keys in All Systems', stats.get('keys_in_all_systems', 0)),
            ('Keys Only in A (Propagation Gaps)', stats.get('keys_only_in_a', 0)),
            ('Keys Missing in A (Out of Authority)', stats.get('keys_missing_in_a', 0)),
            ('Overall Match Rate', f"{stats.get('match_percentage', 0):.1f}%"),
        ],
        'system_counts': sorted(system_counts.items()),
        'discrepancy_summary': [
            ('Out-of-Authority Keys', discrepancy_summary.get('total_out_of_authority', 0)),
            ('Propagation Gaps', discrepancy_summary.get('total_propagation_gaps', 0)),
            ('Duplicate Key Groups', discrepancy_summary.get('total_duplicate_groups', 0)),
        ],
        'propagation_gaps': {system: sorted_list(keys) for system, keys in propagation_gaps.items()},
        'out_of_authority': [
            {
                'normalized_key': key,
                'sources': sources,
            }
            for key, sources in out_of_authority.items()
        ],
        'duplicate_counts': {
            system: len(groups)
            for system, groups in duplicate_keys.items()
        },
        'provisioning': provisioning,
        'keys_only_in_a': sorted_list(keys_only_in_a or []),
        'keys_missing_in_a': sorted_list(keys_missing_in_a or []),
        'system_specific_gaps': {
            system: sorted_list(keys)
            for system, keys in (comparison.get('system_specific_gaps') or {}).items()
        },
        'timestamp': results.get('timestamp'),
    }

    return view


app = create_app()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
