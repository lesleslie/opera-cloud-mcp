# OPERA Cloud MCP - Diagram Reference Guide

This directory contains visual diagrams generated using Mermaid to help understand the OPERA Cloud MCP server architecture and workflows.

## Diagram Files

### Highest Value Diagrams (98% Priority)

#### 1. BaseAPIClient Architecture Diagram

**File**: `base-client-architecture.mmd`
**Location in docs**: `docs/base-client-implementation.md` (after "Key Features Implemented" section)
**Purpose**: Shows the complete architecture of the base HTTP client including all core components (RateLimiter, HealthMonitor, DataTransformer, CircuitBreaker, RequestMetrics) and how they interact with API clients and the OAuth2 Handler.
**Type**: Component Architecture Diagram

#### 2. Security Architecture Diagram

**File**: `security-architecture.mmd`
**Location in docs**: `docs/security-implementation.md` (after "Security Architecture" section)
**Purpose**: Illustrates the complete security infrastructure including SecureOAuthHandler, SecurityMiddleware, AuditLogger, SecurityMonitor, and SecureTokenCache, plus their integration with external alerting and monitoring systems.
**Type**: Layered Security Architecture Diagram

### High Value Diagrams (95% Priority)

#### 3. Project Structure Visualization

**File**: `project-structure.mmd`
**Location in docs**: `docs/implementation-plan.md` (replace ASCII tree in "Project Structure" section)
**Purpose**: Visual representation of the entire project directory structure with module dependencies and relationships.
**Type**: Hierarchical Structure Diagram

#### 4. Circuit Breaker State Machine

**File**: `circuit-breaker-state-machine.mmd`
**Location in docs**: `docs/base-client-implementation.md` (after "Circuit Breaker Pattern" section)
**Purpose**: State diagram showing the three circuit breaker states (Closed, Open, Half-Open) and transition conditions.
**Type**: State Machine Diagram

#### 5. OAuth2 Token Lifecycle

**File**: `oauth2-token-lifecycle.mmd`
**Location in docs**: `docs/security-implementation.md` (after "OAuth2 Token Lifecycle" section)
**Purpose**: Sequence diagram showing token issuance, caching, usage, refresh, and security monitoring throughout the token lifecycle.
**Type**: Sequence Diagram

### High Value Diagrams (90% Priority)

#### 6. Implementation Timeline Gantt Chart

**File**: `implementation-timeline.mmd`
**Location in docs**: `docs/implementation-plan.md` (in "Implementation Phases" section)
**Purpose**: Gantt chart showing the 5-phase implementation plan with timelines for Foundation, Core APIs, Extended Operations, Testing, and Production Readiness.
**Type**: Gantt Chart

#### 7. OAuth2 Authentication Flow

**File**: `oauth2-authentication-flow.mmd`
**Location in docs**: `docs/implementation-plan.md` (in "Authentication Module" section)
**Purpose**: Sequence diagram showing the complete OAuth2 authentication flow from MCP client through token request to API usage.
**Type**: Sequence Diagram

#### 8. Threat Detection Flow

**File**: `threat-detection-flow.mmd`
**Location in docs**: `docs/security-implementation.md` (in "Custom Threat Detection" section)
**Purpose**: Flowchart showing how security events are analyzed, risk scores calculated, and incident responses triggered.
**Type**: Flowchart with Decision Points

#### 9. API Request Lifecycle

**File**: `api-request-lifecycle.mmd`
**Location in docs**: `docs/base-client-implementation.md` (after "BaseAPIClient Class" section)
**Purpose**: Sequence diagram showing the complete lifecycle of an API request through rate limiting, circuit breaking, authentication, and error handling.
**Type**: Sequence Diagram

#### 10. Request Flow with Retry Logic

**File**: `request-flow-retry-logic.mmd`
**Location in docs**: `docs/base-client-implementation.md` (in "Advanced Retry Logic" section)
**Purpose**: Flowchart showing request processing, error classification, retry logic with exponential backoff and jitter, and circuit breaker integration.
**Type**: Complex Flowchart

## How to Use These Diagrams

### Viewing Diagrams

**Option 1: Mermaid Live Editor**

1. Visit [Mermaid Live Editor](https://mermaid.live)
1. Copy the contents of any `.mmd` file
1. Paste into the editor to see the rendered diagram

**Option 2: VS Code Extension**

1. Install the "Mermaid Preview" extension
1. Open any `.mmd` file
1. Right-click → "Mermaid: Open Preview"

**Option 3: Command Line Generation**

```bash
# Using mcp-cli (if available)
mcp mermaid generate docs/diagrams/base-client-architecture.mmd

# Or using the mermaid CLI
npm install -g @mermaid-js/mermaid-cli
mmdc -i docs/diagrams/base-client-architecture.mmd -o docs/diagrams/base-client-architecture.svg
```

**Option 4: Direct Integration**
Many documentation tools support Mermaid natively:

- GitHub/GitLab markdown renders mermaid code blocks
- MkDocs with mermaid2 plugin
- Docusaurus
- Hugo with mermaid shortcode

### Adding to Documentation

To include these diagrams in your markdown files, use:

````markdown
## Architecture

### BaseAPIClient Architecture

```mermaid
path/to/diagram/file.mmd
````

Or inline the mermaid code directly:

```mermaid
graph TB
    ...
```

```

### Modifying Diagrams

All diagrams are stored as `.mmd` (Mermaid source) files, making them:
- **Editable**: Easy to modify with any text editor
- **Version-controllable**: Git can track changes
- **Regeneratable**: Can be re-rendered at any time
- **Searchable**: Text is searchable unlike images

To modify a diagram:
1. Edit the `.mmd` file
2. Preview using one of the methods above
3. Commit changes to Git

### Diagram Conventions

All diagrams follow these conventions:
- **Color coding**: Consistent color scheme across diagrams
  - Blue (#4A90E2): Core components
  - Red (#E74C3C): Error states/critical components
  - Green (#2ECC71): Success states/healthy components
  - Orange (#F39C12): Warnings/monitoring
  - Purple (#9B59B6): Authentication/security
  - Dark Gray (#34495E): External systems
- **Naming**: Descriptive file names using kebab-case
- **Documentation**: Each file has clear purpose statement
- **References**: Files document where they should be referenced

## Contributing New Diagrams

When adding new diagrams:
1. Create as `.mmd` files (not SVG images)
2. Follow the naming convention: `descriptive-name.mmd`
3. Add a reference in this index with:
   - File name
   - Location in documentation
   - Purpose
   - Type
4. Update this README with the new diagram
5. Keep diagrams simple and focused (one concept per diagram)

## Additional Resources

- [Mermaid Documentation](https://mermaid.js.org/)
- [Mermaid Live Editor](https://mermaid.live)
- [Diagram Syntax Guide](https://mermaid.js.org/syntax/flowchart.html)
- [Examples Gallery](https://mermaid.js.org/ecosystem/gallery.html)

---

**Generated**: 2025-01-22
**Total Diagrams**: 10
**All High and Highest Value**: ✅ Complete
```
