# ASD-PROVISIONAL1: <Project Name> Architecture Summary <YYYY-MM-DD>

## Overview
<Brief 3-5 sentence summary of the current architecture, major subsystems, and any notable constraints or principles (e.g., 12-factor, hexagonal, CQRS, microservices vs monolith).>

## Purpose and Scope
- Purpose: <Why this ASD exists and how it’s used>
- Scope: <Codebase/root(s) covered, environments considered, out-of-scope areas>

## Change Context Since Last ASD
<Summarize changes since the previous ASD. Reference ADRs and PRDs completed since last ASD that materially changed architecture.>
- Referenced ADRs: <ADR-IDs and one-line summaries>
- Referenced PRDs: <PRD-IDs and one-line summaries>

## Architecture Principles and Quality Attributes
- Principles: <e.g., simplicity, stability, observability, performance>
- Quality Attributes: <e.g., availability, latency, scalability, maintainability>

## System Modules and Boundaries
<Define your architectural modules (logical boundaries, not necessarily Python packages). For each module include responsibilities, key entities, interfaces, and dependencies.>

### Module: <Module Name>
- Responsibility: <What this module owns>
- Key Entities/Concepts: <Domain objects, services>
- Public Interfaces (provided):
	- <Interface/Service Name>: <Protocol/shape, pre/postconditions>
- Consumed Interfaces (required):
	- <Dependency Name>: <Contract used>
- Data Owned: <Schemas/tables/files/topics>
- Observability: <Logs/metrics/traces used>
- Risks/Notes: <Coupling, hotspots, tech debt>

### Module: <Module Name>
- Responsibility: <...>
... repeat per module ...

## Dependency Graphs
<Describe and visualize dependencies between modules and key external systems. Include an ASCII graph placeholder and a note to generate mermaid/diagrams later.>

```text
<ASCII dependency graph here>
```

Optionally (rendered formats):
```mermaid
graph TD
	<ModuleA> --> <ModuleB>
	<ModuleB> --> <ExternalService>
```

## Interfaces and Contracts
<Document key APIs/CLIs/queues/events between modules and external systems. Include request/response and error modes.>

### Interface: <Name>
- Producer/Owner: <Module>
- Consumer(s): <Modules/Actors>
- Type: <HTTP/GRPC/CLI/Event/DB>
- Endpoint/Topic/Path: <...>
- Request/Input: <schema/shape>
- Response/Output: <schema/shape>
- Errors/Retry/Idempotency: <...>
- Versioning/Compatibility: <...>

## Data Architecture
- Datastores: <Types/engines/instances>
- Schemas: <Key tables/collections with purpose>
- Data flows: <ETL/CDC/streams>
- Retention and Backup: <Policies>
- Privacy/Security: <PII handling, encryption>

## Deployment Architecture
- Environments: <DEV/TEST/STAGE/PROD>
- Topology: <Containers/VMs/Serverless; regions>
- Release Strategy: <Blue/green, canary, rolling>
- Config/Secrets: <How managed>
- Scaling/HA: <Autoscaling, redundancy>

## Observability and Operations
- Logging: <Sinks, levels, correlation>
- Metrics: <SLIs/SLOs, dashboards>
- Tracing: <Tracer, key spans>
- Alerts/Runbooks: <Where and how>

## Security and Compliance
- AuthN/AuthZ: <Mechanisms>
- Network: <Ingress/egress rules>
- Dependencies: <SBOM, updates>
- Compliance: <Standards/regulations>

## Project Structure (Tree) and Notable Classes
<Provide a concise project tree, focusing on key folders and important classes.>

```text
<root>
	<dir>/
		<subdir>/
			<file_or_class.py>  # <purpose>
```

Notable Classes/Files
- <path/to/ClassOrFile>: <Role and why important>


