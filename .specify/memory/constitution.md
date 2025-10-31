<!-- 
SYNC IMPACT REPORT
==================
Version: 1.0.0 (new constitution - initial)
Ratified: 2025-10-28
Status: Complete

CHANGES:
- Created 5 core principles: Code Quality, Testing Standards, Type Safety, User Experience, Performance
- Added Security & Azure Best Practices section
- Added Development Workflow & Quality Gates section
- Established governance procedures and amendment rules

TEMPLATES TO UPDATE:
- ✅ .specify/templates/spec-template.md (aligned with principles)
- ✅ .specify/templates/tasks-template.md (aligned with testing principle)
- ✅ .specify/templates/plan-template.md (performance goals section ready)

FOLLOW-UP TODOS:
- None - constitution is complete and binding
-->

# Azure AI POC Constitution

**Project Name**: Azure AI Proof of Concept  
**Technology Stack**: Python 3.11 (FastAPI), React 19 (TypeScript), Azure Cloud Services  
**Primary Purpose**: Document intelligence and conversational AI platform with multi-tenant support

---

## Core Principles

### I. Code Quality (Non-Negotiable)

**Standard**: All code MUST pass ruff linting, mypy strict type checking, and code review before merge.

**Rules**:
- Python backend: ruff with `E, W, F, I, B, C4, UP` rules; line-length=100
- React frontend: ESLint configuration per `.eslintrc.yml`
- TypeScript: strict mode enabled; no `any` types without documented justification
- Type annotations MUST be complete in all modules (mypy: `disallow_untyped_defs = true`)
- Imports MUST be sorted (isort via ruff)
- All code MUST follow BC Government design system standards (frontend)

**Rationale**: Type safety and consistent code style prevent runtime errors, improve maintainability, and reduce cognitive load during code reviews. Strict mypy enforcement catches classes of bugs at compile time.

**Compliance Check**: Run linting in CI/CD; fail PRs that violate these rules. Use pre-commit hooks locally.

---

### II. Test-First Development (Non-Negotiable)

**Standard**: Tests MUST be written before implementation; TDD cycle strictly enforced.

**Rules**:
- Write test specifications first → Get user/stakeholder approval → Write tests → Ensure tests fail → Implement → Tests pass
- Backend tests: pytest with minimum 35% coverage overall, 75%+ for core modules (`app/core/*`, `app/middleware/*`)
- Frontend tests: vitest with integration and unit tests for all user-facing components
- Integration tests MUST cover: Service-to-service communication, Azure service interactions, multi-tenant workflows
- Contract tests MUST be present for all API endpoints (request/response validation)
- No feature can be marked complete without passing tests

**Rationale**: Writing tests first forces thinking about edge cases, clarifies requirements, and ensures testability. High coverage on core modules prevents reliability regressions in critical paths.

**Coverage Thresholds**:
- Backend overall: 35% (fail_under threshold)
- Backend core modules: 75%+
- Backend middleware: 75%+
- Frontend: 60%+ (aspirational, enforced in critical flows)

**Compliance Check**: CI/CD enforces coverage gates; SonarCloud integration reports coverage; PRs failing coverage checks cannot merge.

---

### III. Type Safety & Static Analysis

**Standard**: All code MUST be statically analyzable; runtime type verification encouraged where feasible.

**Rules**:
- Python backend: mypy strict mode on all modules
  - `disallow_untyped_defs = true`
  - `disallow_incomplete_defs = true`
  - `check_untyped_defs = true`
  - `disallow_untyped_decorators = true`
- React/TypeScript: no implicit `any`; use union types and discriminated unions for state management
- Pydantic models MUST be used for all API request/response validation
- Database models MUST have type annotations (Cosmos DB, etc.)
- Exceptions: FastAPI dependency injection (B008) allowed; document justifications in code comments

**Rationale**: Type safety catches entire classes of bugs (NameError, AttributeError, etc.) before runtime. Pydantic validation ensures data integrity at service boundaries.

**Compliance Check**: mypy, ESLint, TypeScript compiler all run in CI/CD; failures block merge.

---

### IV. User Experience Consistency (Non-Negotiable)

**Standard**: All user-facing features MUST follow BC Government design guidelines; UX decisions MUST be documented and consistent across all journeys.

**Rules**:
- UI components MUST use `@bcgov/design-system-react-components` exclusively
- Font stack MUST use `@bcgov/bc-sans`
- Color palette, spacing, and sizing MUST comply with BC design system
- All interactive elements MUST have:
  - Hover states defined
  - Focus states for keyboard navigation (WCAG 2.1 AA minimum)
  - Loading states for async operations
  - Error states with user-friendly messages
  - Accessibility attributes (aria-labels, aria-describedby, etc.)
- Transitions and animations MUST reduce motion for users with motion sensitivity
- Error messages MUST be specific, actionable, and plain language
- No feature can include UX that contradicts prior design decisions without documentation

**Rationale**: Consistency reduces cognitive load, improves accessibility, and builds user trust. BC government applications MUST comply with accessibility standards for public sector.

**Compliance Check**: UX review checklist in spec.md; accessibility audit in PR review; design system component usage enforced via code review.

---

### V. Performance & Observability

**Standard**: All features MUST meet performance targets; observability MUST be built in from first commit.

**Rules**:
- API endpoints: p95 response time ≤ 500ms for standard queries; p99 ≤ 2s
- Frontend page load: Time to Interactive (TTI) ≤ 3s on 4G connections
- Frontend component rendering: No single render > 16ms (60fps standard)
- All services MUST emit structured logs (structlog format)
- Distributed tracing MUST be configured via OpenTelemetry (OTLP exporter)
- Metrics MUST be exposed on Prometheus format (/metrics endpoint)
- Critical paths MUST have alerts configured (request errors, latency, database failures)
- Database queries MUST be monitored; slow queries (>100ms) MUST be optimized before release

**Instrumentation Requirements**:
- All HTTP endpoints: auto-instrumented via `opentelemetry-instrumentation-fastapi`
- All outbound HTTP calls: instrumented via `opentelemetry-instrumentation-httpx`
- Custom instrumentation for business logic (AI agent workflows, document processing)

**Rationale**: Performance affects user satisfaction and system reliability. Observable systems enable rapid incident response and proactive capacity planning. Azure Landing Zone includes monitoring; we MUST use it.

**Compliance Check**: Performance benchmarks run in CI/CD; observability checklist in implementation; production deployments require monitoring validation.

---

## Security & Azure Best Practices

**Standard**: All security decisions MUST align with Azure Landing Zone policies; all infrastructure MUST be immutable and infrastructure-as-code.

**Rules**:
- Private endpoints MUST be used for all PaaS services (Cosmos DB, Azure Search, Azure Cognitive Services)
- Private DNS zones MUST be properly linked to VNets; DNS forwarding MUST route through centralized hub resolver
- Network Security Groups (NSGs) MUST be configured for all subnets with deny-by-default ingress rules
- All secrets MUST be stored in Azure Key Vault; NO hardcoded credentials in code or configuration
- Environment variables MUST use Key Vault references in production
- API authentication MUST use JWT tokens from Keycloak (dev.loginproxy.gov.bc.ca)
- Rate limiting MUST be enabled on all public endpoints (slowapi + Redis backend)
- CORS MUST be restricted to known origins; no `*` in production
- All Terraform modules MUST use Azure Verified Modules (AVM) where available
- No manual Azure resource creation; all infrastructure MUST be in Terraform

**Rationale**: Azure Landing Zone is a controlled environment with security policies. Non-compliance risks security audits, compliance violations, and service disruption.

**Compliance Check**: Security review in PR; infrastructure code review; pre-deployment checklist.

---

## Development Workflow & Quality Gates

**Standard**: All features MUST follow a standardized workflow with defined quality gates before release.

**Workflow Phases**:

1. **Planning** (Gates: Charter clear, stakeholder alignment)
   - Spec created with user stories, acceptance criteria, requirements
   - Research completed; technical approach documented
   - Data models and API contracts generated

2. **Design** (Gates: Spec approved, no NEEDS CLARIFICATION, design review passed)
   - Implementation plan created
   - Task list with phases and dependencies defined
   - Team capacity and timeline agreed

3. **Development** (Gates: Code review passed, tests passing, coverage thresholds met)
   - Phase 1: Setup and shared infrastructure
   - Phase 2: Foundational services (blocking prerequisites)
   - Phase 3+: User stories in priority order
   - Each phase: Tests → Models → Services → Integration
   - No story merge until all gates passed

4. **Integration** (Gates: Integration tests passing, observability verified, performance benchmarks met)
   - Feature tested end-to-end with real data
   - Monitoring dashboards and alerts configured
   - Performance validated against targets
   - Security review completed

5. **Deployment** (Gates: QA sign-off, deployment procedure documented, rollback plan ready)
   - Staging environment validation
   - Production deployment (blue-green or canary)
   - Post-deployment monitoring for 1 hour minimum

**Quality Gates** (Cannot proceed without passing):
- ✅ Code passes ruff + mypy + ESLint + TypeScript compiler
- ✅ Tests pass (unit, integration, contract)
- ✅ Code coverage meets thresholds
- ✅ SonarCloud analysis passes quality gate
- ✅ Security review approved
- ✅ UX review approved (if user-facing)
- ✅ Performance benchmarks met
- ✅ Documentation updated
- ✅ 2+ peer code reviews approved

**Rationale**: Quality gates prevent technical debt accumulation, ensure predictable delivery, and maintain system reliability.

**Compliance Check**: GitHub branch protection rules; PR checklist; CI/CD status checks.

---

## Governance

**Authority**: This constitution supersedes all other project guidelines and practices. The Public Cloud team (hub administration) owns the Azure Landing Zone policies; development teams own code quality and testing standards.

**Amendment Procedure**:
1. Amendment proposed in PR with clear justification
2. Discussion in team sync (minimum 3 days open comment period)
3. Ratification: unanimous consent preferred; majority vote acceptable for non-breaking amendments
4. Documented in constitution with new version number and effective date
5. All affected templates and processes updated before enforcement

**Versioning Policy**:
- MAJOR: Breaking changes (e.g., removing principle, incompatible tooling)
- MINOR: Adding principle, expanding requirements, clarifying guidance
- PATCH: Wording clarifications, process improvements, threshold adjustments

**Compliance Review**:
- Monthly: Constitution compliance audit (coverage trends, quality gates enforcement)
- Quarterly: Principle effectiveness review
- Annually: Complete constitution assessment and possible refresh

**Monitoring & Enforcement**:
- CI/CD: Automated linting, testing, coverage gates
- Code Review: Peer verification of principle compliance
- Metrics Dashboard: Real-time view of quality indicators
- Incident Review: Post-incident retrospectives evaluate principle effectiveness
- Team Training: Quarterly architecture & best practices sessions

**Exceptions & Waivers**:
- Temporary exceptions require written justification, stakeholder approval, and explicit remediation plan
- No exception granted for Code Quality, Test-First, or Type Safety principles
- Exceptions must be documented in issue tracking (linked to commit)
- Exceptions expire after 1 sprint; renewal requires fresh justification

---

## References & Standards

**Azure Landing Zone**:
- Documentation: `.github/instructions/azure-networking.instructions.md`
- Networking: Hub-and-spoke model with centralized DNS, private endpoints mandatory
- Compliance: All resources must comply with organizational policy (NSGs, private DNS zones, private subnets)

**Code Quality Standards**:
- Backend: Ruff (E,W,F,I,B,C4,UP), mypy strict, pytest, SonarCloud
- Frontend: ESLint, TypeScript strict, vitest, SonarCloud
- DevOps: Terraform with Azure Verified Modules, infrastructure-as-code only

**Testing Frameworks**:
- Backend: pytest + pytest-asyncio + pytest-cov + pytest-mock (FastAPI applications)
- Frontend: vitest + @testing-library/react + msw (mocking)
- Contracts: pytest for API request/response validation

**Observability Stack**:
- Logging: structlog (Python), structured logs to central sink
- Tracing: OpenTelemetry SDK + OTLP exporter
- Metrics: Prometheus client, exposed on `/metrics`
- Monitoring: Azure Monitor integration; dashboards for critical paths

**Documentation**:
- Feature specs: `.specify/templates/spec-template.md`
- Implementation plans: `.specify/templates/plan-template.md`
- Task breakdown: `.specify/templates/tasks-template.md`
- Contracts: OpenAPI schemas in `specs/[###-feature]/contracts/`
- Architecture decisions: ADRs (Architecture Decision Records) in `docs/adr/`
- DONOT produce markdown for documentation after each task until explicitly asked.

---

**Version**: 1.0.0 | **Ratified**: 2025-10-28 | **Last Amended**: 2025-10-28
