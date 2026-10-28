# AI Repository Architect

## Mission

Build a production-grade agentic AI system that can analyze any public GitHub repository and generate professional software architecture documentation automatically.

The system must go far beyond simple repository summarization.

It should understand:

- Project purpose
- Business logic
- Architecture
- Code relationships
- Call flows
- Dependencies
- Database interactions
- API design
- Security considerations
- Design patterns

and produce professional documentation similar to what a senior software architect would write.

---

# Core User Flow

User submits:

```text
https://github.com/owner/repository
```

System performs:

1. Clone repository
2. Detect language(s)
3. Detect framework(s)
4. Parse source code
5. Build AST
6. Build dependency graph
7. Build call graph
8. Build repository knowledge graph
9. Run multi-agent analysis
10. Generate reports
11. Generate diagrams
12. Export documentation

---

# Primary Deliverables

For every repository generate:

## Executive Summary

Explain:

- What the project does
- Problem it solves
- Target users
- High-level architecture
- Main technologies

---

## Tech Stack Analysis

Detect:

- Languages
- Frameworks
- Libraries
- Build tools
- Databases
- Cloud providers
- Message queues
- Infrastructure

Example output:

```json
{
  "frontend": "Next.js",
  "backend": "FastAPI",
  "database": "PostgreSQL",
  "cache": "Redis",
  "orm": "Prisma"
}
```

---

## Repository Structure

Explain:

```text
src/
api/
services/
models/
database/
```

Purpose of every major folder.

---

## Architecture Analysis

Determine architecture style:

- Monolith
- Modular Monolith
- Microservices
- Event Driven
- Hexagonal
- Clean Architecture
- Layered Architecture
- CQRS
- Domain Driven Design

Generate explanation.

---

## Module Breakdown

For every module explain:

- Responsibility
- Public interfaces
- Dependencies
- Internal flow

---

## API Documentation

Detect:

- REST APIs
- GraphQL
- gRPC
- WebSockets

Generate:

- Endpoint list
- Request schemas
- Response schemas
- Authentication requirements

---

## Database Analysis

Detect:

- ORM models
- SQL schemas
- Migrations

Generate:

- Entity descriptions
- Relationships
- ERD

---

## Authentication Analysis

Explain:

- Login flow
- Session handling
- JWT usage
- OAuth providers
- Permissions
- Role management

---

## Security Analysis

Identify:

- Hardcoded secrets
- Unsafe patterns
- SQL injection risks
- Missing validation
- Missing authorization checks

Generate security report.

---

## Design Pattern Detection

Identify:

- Factory
- Singleton
- Strategy
- Adapter
- Observer
- Repository
- Service Layer

Generate explanation.

---

## Dependency Analysis

Generate:

- Internal dependency graph
- External dependency graph

Detect:

- Circular dependencies
- Unused dependencies

---

# Diagram Generation

Generate Mermaid diagrams.

## Architecture Diagram

```mermaid
flowchart TD
```

---

## Sequence Diagrams

Generate major business flows.

Example:

Login

```mermaid
sequenceDiagram
```

---

## Flow Diagrams

Generate user journey flows.

```mermaid
flowchart TD
```

---

## Class Diagrams

```mermaid
classDiagram
```

---

## ER Diagrams

```mermaid
erDiagram
```

---

# Repository Knowledge Graph

Build graph entities:

- File
- Module
- Function
- Class
- API Endpoint
- Database Table
- Service

Relationships:

- imports
- calls
- extends
- implements
- uses
- queries

Store graph for future retrieval.

---

# Agent Architecture

Implement using LangGraph.

Create specialized agents.

## Repo Agent

Responsibilities:

- Clone repository
- Read structure
- Detect languages

---

## Parsing Agent

Responsibilities:

- Tree-sitter parsing
- AST generation

---

## Architecture Agent

Responsibilities:

- Architecture analysis
- Layer detection
- Pattern detection

---

## Backend Agent

Responsibilities:

- API analysis
- Service analysis

---

## Frontend Agent

Responsibilities:

- Component analysis
- Routing analysis
- State management analysis

---

## Database Agent

Responsibilities:

- Schema analysis
- Query analysis

---

## Security Agent

Responsibilities:

- Security review

---

## Diagram Agent

Responsibilities:

- Mermaid generation

---

## Documentation Agent

Responsibilities:

- Produce final reports

---

# Supported Languages

Must support:

- Python
- TypeScript
- JavaScript
- Java
- Go
- Rust
- C#
- PHP

Use Tree-sitter parsers.

---

# Storage Layer

Use:

- PostgreSQL
- Neo4j
- Vector Database

Store:

- Repository metadata
- Knowledge graph
- Embeddings

---

# RAG Requirements

Do NOT use naive chunking.

Required pipeline:

Repository
→ AST
→ Dependency Graph
→ Call Graph
→ Knowledge Graph
→ Embeddings
→ LLM Analysis

Preserve relationships between files.

---

# Output Formats

Generate:

## Markdown

architecture.md

api.md

database.md

security.md

onboarding.md

---

## JSON

machine-readable analysis

---

## Mermaid

diagram files

---

## PDF

final executive report

---

# Tech Stack

Backend:

- Python
- FastAPI

Agent Framework:

- LangGraph

Parsing:

- Tree-sitter

Graph:

- Neo4j

Vector DB:

- Qdrant

Database:

- PostgreSQL

Queue:

- Celery + Redis

LLM Layer:

- Claude
- GPT
- Gemini

Use model routing.

---

# Frontend

Build React dashboard.

Features:

- Repository submission
- Analysis progress
- Architecture explorer
- Graph viewer
- Diagram viewer
- Chat with repository
- Documentation viewer

---

# Success Criteria

The generated report should be detailed enough that a new engineer can understand the repository without reading most of the source code.

The architecture explanation should resemble documentation written by a senior software architect.

The system must scale to repositories containing hundreds of thousands of lines of code.
