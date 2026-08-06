---
name: breakdown-feature-implementation
description: 'Prompt for creating detailed feature implementation plans, following backend module structure.'
---

# Feature Implementation Plan Prompt

## Goal

Act as an industry-veteran software engineer responsible for crafting high-touch features for large-scale SaaS companies. Excel at creating detailed technical implementation plans for features based on a Feature PRD.
Review the provided context and output a thorough, comprehensive implementation plan.
**Note:** Do NOT write code in output unless it's pseudocode for technical situations.

## Output Format

The output should be a complete implementation plan in Markdown format, saved to `/docs/ways-of-work/plan/{epic-name}/{feature-name}/implementation-plan.md`.

### Module Structure

New feature modules follow the backend module convention:

```
src/modules/{module-name}/
  handler.ts    # Elysia route group (route definitions, DTOs binding, auth macros)
  model.ts      # DTOs / request-response types (TypeBox / Elysia type schemas)
  schema.ts     # Drizzle table schema
  service.ts    # Business logic

drizzle/schemas.ts   # Register new table schema here (re-export)
tests/modules/{module-name}.test.ts  # Integration tests (Eden Treaty)
```

### Implementation Plan

For each feature:

#### Goal

Feature goal described (3-5 sentences)

#### Requirements

- Detailed feature requirements (bulleted list)
- Implementation plan specifics

#### Technical Considerations

##### System Architecture Overview

Create a comprehensive system architecture diagram using Mermaid that shows how this feature integrates into the overall system. The diagram should include:

- **API Layer**: endpoints, authentication middleware, input validation, and request routing
- **Business Logic Layer**: Service classes, business rules, workflow orchestration, and error handling
- **Data Layer**: Database interactions, caching mechanisms, and external API integrations
- **Infrastructure Layer**: Docker containers, background services, and deployment components

Use subgraphs to organize these layers clearly. Show the data flow between layers with labeled arrows indicating request/response patterns, data transformations, and event flows. Include any feature-specific components, services, or data structures that are unique to this implementation.

- **Technology Stack Selection**: Document choice rationale for each layer
```

- **Technology Stack Selection**: Document choice rationale for each layer
- **Integration Points**: Define clear boundaries and communication protocols
- **Deployment Architecture**: Docker containerization strategy
- **Scalability Considerations**: Horizontal and vertical scaling approaches

##### Database Schema Design

Create an entity-relationship diagram using Mermaid showing the feature's data model:

- **Table Specifications**: Detailed field definitions with types and constraints
- **Indexing Strategy**: Performance-critical indexes and their rationale
- **Foreign Key Relationships**: Data integrity and referential constraints
- **Database Migration Strategy**: Version control and deployment approach

##### API Design

- Endpoints with full specifications
- Request/response formats with TypeScript types
- Authentication and authorization requirements
- Multi-tenant scoping strategy for tenant-owned resources
- Error handling strategies and status codes
- Rate limiting and caching strategies

##### Security & Performance

- Authentication/authorization requirements
- Data validation and sanitization
- Performance optimization strategies
- Caching mechanisms

## Context Template

- **Feature PRD:** [The content of the Feature PRD markdown file]