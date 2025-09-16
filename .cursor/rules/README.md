# Cursor Rules Collection

This directory contains AI-powered development workflow rules for Cursor IDE. These rules provide structured, systematic approaches to common development tasks, ensuring consistency and quality across your development process.

## 📁 Available Workflows

### 🎯 [PRD-Driven Workflow](./prd-driven-workflow/)
Transform ideas into shipped features through structured requirements and systematic execution.

**Use when:** Building new features from user requirements, need clear documentation before implementation.

**Files:**
- `01-create-prd.mdc` - Create comprehensive Product Requirements Documents
- `02-generate-tasks.mdc` - Break down PRDs into actionable task hierarchies  
- `03-process-tasks.mdc` - Execute tasks systematically with testing and commits

### 🏗️ [Architecture Design Workflow](./architecture-design-workflow/)
Design robust system architectures with comprehensive analysis and stakeholder alignment.

**Use when:** Designing new systems, major architectural changes, or technical decision-making.

**Files:**
- `01-define-architecture-requirements.mdc` - Define comprehensive architecture requirements
- `02-propose-architecture-options.mdc` - Generate and compare viable alternatives
- `03-create-technical-design.mdc` - Create detailed technical design documents
- `04-architecture-signoff-and-readiness.mdc` - Facilitate stakeholder review and approval

### 🔍 [Review-Driven Workflow](./review-driven-workflow/)
Comprehensive code review system with specialized multi-perspective analysis.

**Use when:** Reviewing code changes, ensuring quality standards, or providing educational feedback.

**Files:**
- `01-initiate-review.mdc` - Start comprehensive review process
- `02-generate-review-tasks.mdc` - Convert review plans into actionable tasks
- `03-execute-review-process.mdc` - Execute review tasks and generate analysis
- `04-publish-review-results.mdc` - Publish results and create documentation

### 🔧 [Refactoring & Tech Debt Workflow](./refactoring-tech-debt-workflow/)
Identify, plan, and execute systematic refactoring to reduce technical debt.

**Use when:** Improving code quality, addressing technical debt, or modernizing legacy systems.

**Files:**
- `01-identify-tech-debt.mdc` - Identify and document technical debt
- `02-plan-refactoring-tasks.mdc` - Plan and prioritize refactoring tasks
- `03-execute-refactoring.mdc` - Execute refactoring safely and systematically
- `04-validate-and-measure.mdc` - Validate success and measure improvements

### 🧪 [Test Generation Workflow](./test-generation-workflow/)
Generate comprehensive test suites with systematic coverage analysis.

**Use when:** Improving test coverage, creating test plans, or ensuring quality assurance.

**Files:**
- `01-analyze-code-for-testing.mdc` - Analyze code components for testing requirements
- `02-generate-test-cases.mdc` - Generate comprehensive test cases
- `03-create-test-plan.mdc` - Create comprehensive test plans for features
- `04-execute-and-maintain-tests.mdc` - Execute test suites and maintain quality

## 🚀 Quick Start

### Basic Usage

1. **Choose the appropriate workflow** based on your current task
2. **Invoke the first rule** in the workflow sequence
3. **Follow the guided process** through each step
4. **Complete the workflow** systematically

### Example Workflow Invocation

```bash
# Start a new feature development
@prd-driven-workflow/01-create-prd

# Review existing code
@review-driven-workflow/01-initiate-review

# Plan system architecture
@architecture-design-workflow/01-define-architecture-requirements
```

## 📋 Workflow Selection Guide

| Task Type | Recommended Workflow | Starting Rule |
|-----------|---------------------|---------------|
| **New Feature Development** | PRD-Driven | `01-create-prd.mdc` |
| **System Design** | Architecture Design | `01-define-architecture-requirements.mdc` |
| **Code Review** | Review-Driven | `01-initiate-review.mdc` |
| **Code Quality Improvement** | Refactoring & Tech Debt | `01-identify-tech-debt.mdc` |
| **Test Coverage** | Test Generation | `01-analyze-code-for-testing.mdc` |

## 🔄 Workflow Integration

### Sequential Workflows
Many workflows can be chained together for comprehensive development:

```
PRD-Driven → Architecture Design → Test Generation → Review-Driven
```

### Parallel Workflows
Some workflows can run in parallel:

```
Refactoring & Tech Debt ↕ Test Generation
```

## ⚙️ Configuration

### Rule Activation
- **Manual Invocation**: Use `@workflow-name/rule-name` syntax
- **Auto-Attachment**: Rules with `globs` patterns activate automatically
- **Always Apply**: Rules with `alwaysApply: true` run on all files

### Customization
Each workflow can be customized by:
1. Modifying rule parameters in MDC front matter
2. Adjusting glob patterns for auto-attachment
3. Adding project-specific validation criteria

## 📊 Best Practices

### General Guidelines
1. **Start with requirements** - Use PRD-Driven for new features
2. **Design before coding** - Use Architecture Design for complex systems
3. **Review systematically** - Use Review-Driven for quality assurance
4. **Refactor regularly** - Use Refactoring workflow to manage tech debt
5. **Test comprehensively** - Use Test Generation for quality coverage

### Workflow-Specific Tips
- **PRD-Driven**: Be thorough with clarifying questions
- **Architecture Design**: Consider multiple alternatives before deciding
- **Review-Driven**: Use specialized reviewers for different aspects
- **Refactoring**: Measure improvements to validate success
- **Test Generation**: Focus on edge cases and error conditions

## 🛠️ Troubleshooting

### Common Issues

**Issue**: Rules not activating automatically  
**Solution**: Check glob patterns in MDC front matter

**Issue**: Workflow steps out of sequence  
**Solution**: Follow numbered sequence, complete prerequisites

**Issue**: Generated outputs not meeting standards  
**Solution**: Review quality gates in workflow documentation

### Getting Help
1. Check individual workflow README files for detailed guidance
2. Review example outputs in `/tasks/` directory
3. Consult team members familiar with the workflows
4. Submit issues for workflow improvements

## 📈 Metrics and Tracking

### Workflow Effectiveness
Track these metrics to measure workflow success:

- **Time to completion** for each workflow phase
- **Quality metrics** (defect rates, test coverage)
- **Team adoption** rates and feedback
- **Rework rates** and iteration cycles

### Continuous Improvement
- Regular retrospectives on workflow effectiveness
- Updates based on team feedback and lessons learned
- Integration of new best practices and tools
- Documentation updates reflecting real-world usage

## 🤝 Contributing

### Workflow Improvements
We welcome contributions to enhance these workflows:

1. **New Rules**: Add specialized rules for specific scenarios
2. **Enhanced Logic**: Improve existing rule logic and validation
3. **Documentation**: Better examples and troubleshooting guides
4. **Integration**: Better tool and platform integrations

### Contribution Process
1. Fork the repository
2. Create a feature branch for your improvements
3. Test workflows with real projects
4. Submit pull request with detailed description
5. Participate in review process

## 📄 License

These workflows are part of the AI Developer Workflows collection and follow the Apache 2.0 license terms. See the parent repository for full licensing details.

---

## 🔗 Related Resources

- **Cursor Documentation**: https://docs.cursor.com/
- **AI Developer Workflows**: Parent repository with additional tools
- **Best Practices Guide**: Team-specific development standards
- **Project Templates**: Starter templates using these workflows

---

*Built with ❤️ for developers who believe in systematic, AI-assisted development*
