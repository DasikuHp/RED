# Requirements Document: SEAL Engine & A/B Tracker

## Overview

The SEAL (Systematic Email Analysis & Learning) Engine analyzes email campaign performance to generate AI-powered improvement suggestions. The A/B Tracker determines optimal email variants for leads based on historical performance data. Together they optimize email marketing campaign effectiveness through data-driven decisions.

## Functional Requirements

### FR1: SEAL Engine Analysis Cycle
**ID**: FR-SEAL-001
**Description**: The system shall execute a complete SEAL analysis cycle that queries campaign performance data, identifies low performers, generates improvement suggestions, and creates a markdown report.
**Acceptance Criteria**:
- AC1: Database query returns campaign performance grouped by category and variant
- AC2: Campaigns with open_rate < 0.20 are identified as low performers
- AC3: AI-generated improvement suggestions are created for each low performer
- AC4: Markdown report is written to Obsidian or fallback log directory
- AC5: Analysis summary statistics are returned in structured format

### FR2: Campaign Performance Query
**ID**: FR-SEAL-002
**Description**: The system shall query the database to retrieve email campaign performance metrics including open rates, click rates, and reply rates grouped by business category and email variant.
**Acceptance Criteria**:
- AC1: Query includes all campaigns from the campaigns table
- AC2: Performance metrics are calculated correctly (open_rate = opens/total_sent)
- AC3: Results are grouped by categoria and variant fields
- AC4: Query handles missing or null data gracefully

### FR3: AI-Powered Improvement Generation
**ID**: FR-SEAL-003
**Description**: For campaigns identified as low performers, the system shall generate improved email subject lines using OpenAI's GPT models.
**Acceptance Criteria**:
- AC1: OpenAI API is called with appropriate prompt engineering
- AC2: Generated suggestions include rationale and confidence score
- AC3: Suggestions are saved to seal_insights database table
- AC4: API failures are handled gracefully with fallback behavior

### FR4: Markdown Report Generation
**ID**: FR-SEAL-004
**Description**: The system shall generate a comprehensive markdown report summarizing the analysis results, including performance metrics, low performers, and improvement suggestions.
**Acceptance Criteria**:
- AC1: Report includes date, analyzed campaign count, and summary statistics
- AC2: Low performers are listed with their original and improved subject lines
- AC3: Report is written to Obsidian via obsidian_bridge.py
- AC4: If Obsidian unavailable, report is written to local logs directory

### FR5: A/B Variant Selection
**ID**: FR-AB-001
**Description**: The system shall determine the optimal email variant (A or B) for a given lead based on historical performance data for the lead's business category.
**Acceptance Criteria**:
- AC1: Function accepts lead_id and categoria parameters
- AC2: Returns "A" or "B" string
- AC3: Decision is deterministic for same inputs
- AC4: Performance data is queried from ab_experiments table

### FR6: Performance-Based Decision Logic
**ID**: FR-AB-002
**Description**: The A/B tracker shall implement decision logic that selects variants based on performance data, with fallback to random selection when data is insufficient.
**Acceptance Criteria**:
- AC1: If <10 sends per variant: returns random choice seeded by lead_id
- AC2: If both variants present: returns better performing variant
- AC3: If only one variant available: returns that variant
- AC4: If no data: returns "A" as fallback

### FR7: Variant Performance Scoring
**ID**: FR-AB-003
**Description**: The system shall calculate a composite performance score for each variant based on open rate, click rate, and reply rate.
**Acceptance Criteria**:
- AC1: Score calculation uses weighted metrics (open_rate: 0.5, click_rate: 0.3, reply_rate: 0.2)
- AC2: Same scoring formula applied to both variants
- AC3: Scores are normalized between 0.0 and 1.0
- AC4: Calculation handles edge cases (division by zero)

### FR8: Decision Logging
**ID**: FR-AB-004
**Description**: All A/B decisions shall be logged with context including lead_id, categoria, selected variant, and decision reason.
**Acceptance Criteria**:
- AC1: Decision reason codes are documented and consistent
- AC2: Logs include timestamp and performance context
- AC3: Logs are stored in database or file for analytics
- AC4: Log format supports future analysis and reporting

## Non-Functional Requirements

### NFR1: Performance
**ID**: NFR-PERF-001
**Description**: The SEAL analysis cycle shall complete within 5 minutes for up to 1000 campaigns.
**Acceptance Criteria**:
- AC1: Database queries complete within 30 seconds
- AC2: OpenAI API calls complete within 2 minutes total
- AC3: Report generation completes within 30 seconds
- AC4: Memory usage remains under 500MB

### NFR2: Reliability
**ID**: NFR-RELI-001
**Description**: The system shall handle failures gracefully with appropriate fallback mechanisms.
**Acceptance Criteria**:
- AC1: Database connection failures trigger retry logic
- AC2: OpenAI API failures skip suggestion generation but continue analysis
- AC3: Obsidian failures trigger fallback to local log directory
- AC4: All external dependencies have timeout and retry configurations

### NFR3: Deterministic Behavior
**ID**: NFR-DET-001
**Description**: The A/B tracker shall produce deterministic results for the same inputs.
**Acceptance Criteria**:
- AC1: Same lead_id and categoria always produce same variant
- AC2: Random fallback uses lead_id as seed for reproducibility
- AC3: Performance data queries are consistent and repeatable
- AC4: Score calculations produce same results for same inputs

### NFR4: Security
**ID**: NFR-SEC-001
**Description**: The system shall protect sensitive data including API keys and database credentials.
**Acceptance Criteria**:
- AC1: OpenAI API key stored in environment variables
- AC2: Database credentials not hardcoded in source
- AC3: Error messages do not leak sensitive information
- AC4: Input validation prevents SQL injection

### NFR5: Maintainability
**ID**: NFR-MAINT-001
**Description**: The code shall be well-structured, documented, and follow Python best practices.
**Acceptance Criteria**:
- AC1: Code includes type hints for all functions
- AC2: Functions have docstrings with parameter descriptions
- AC3: Error handling is consistent across modules
- AC4: Configuration is centralized in config.py

## Technical Constraints

### TC1: Database Schema
**ID**: TC-DB-001
**Description**: The system must work with existing database schema defined in db.py.
**Constraints**:
- Must use existing tables: campaigns, ab_experiments, seal_insights
- Must respect foreign key relationships
- Must use existing field names and data types
- Must maintain data integrity

### TC2: External Dependencies
**ID**: TC-DEPS-001
**Description**: The system must integrate with existing components.
**Constraints**:
- Must use existing config.py for configuration
- Must use existing obsidian_bridge.py for Obsidian integration
- Must use loguru for logging (already in project)
- Must use existing database connection patterns

### TC3: File Structure
**ID**: TC-FILE-001
**Description**: Files must be placed in specific locations as requested.
**Constraints**:
- seal_engine.py must be in E:\RED\06_seal\seal_engine.py
- ab_tracker.py must be in E:\RED\06_seal\ab_tracker.py
- __init__.py must be updated in E:\RED\06_seal\__init__.py
- Logs must go to E:\RED\logs\ or Obsidian 04_seal_logs\

### TC4: Python Version
**ID**: TC-PYTHON-001
**Description**: The system must work with Python 3.8+.
**Constraints**:
- Must use syntax compatible with Python 3.8
- Must use standard library features available in 3.8
- Must not require Python 3.9+ specific features
- Type hints must be compatible with 3.8

## Data Requirements

### DR1: Campaign Performance Data
**ID**: DR-DATA-001
**Description**: The system requires campaign performance data from the campaigns table.
**Data Elements**:
- lead_id, email_subject, variant, sent_at
- opened, opened_at, clicked, clicked_at, replied, replied_at
- Calculated metrics: open_rate, click_rate, reply_rate

### DR2: A/B Experiment Data
**ID**: DR-DATA-002
**Description**: The system requires A/B experiment performance data from ab_experiments table.
**Data Elements**:
- categoria, template_version, variant
- total_sent, opens, clicks, replies, conversions
- Calculated metrics: open_rate, click_rate, reply_rate, conversion_rate

### DR3: SEAL Insights Storage
**ID**: DR-DATA-003
**Description**: The system must store generated improvement suggestions in seal_insights table.
**Data Elements**:
- run_date, segment_type, segment_value
- metric_name, metric_value, suggestion
- applied flag (0/1), created_at timestamp

## Interface Requirements

### IR1: Function Interfaces
**ID**: IR-API-001
**Description**: Public functions must have clearly defined interfaces.
**Requirements**:
- run_seal_cycle() -> dict (SEALResult)
- get_variant(lead_id: int, categoria: str) -> str
- All parameters documented with types
- Return types clearly specified

### IR2: Error Interface
**ID**: IR-API-002
**Description**: Error handling must follow consistent patterns.
**Requirements**:
- Database errors raise sqlite3.Error
- API errors raise appropriate exception types
- Validation errors raise ValueError
- All exceptions include descriptive messages

### IR3: Configuration Interface
**ID**: IR-API-003
**Description**: Configuration must be accessed through config.py.
**Requirements**:
- Use Config.llm_base_url for OpenAI API
- Use Config.obsidian_url for Obsidian bridge
- Database path hardcoded as r"E:\RED\red.db"
- Environment variables loaded via dotenv

## Quality Attributes

### QA1: Testability
**ID**: QA-TEST-001
**Description**: The system must be designed for testability.
**Attributes**:
- Functions are pure where possible
- External dependencies can be mocked
- Database queries can be tested with in-memory SQLite
- Configuration can be overridden for testing

### QA2: Observability
**ID**: QA-OBS-001
**Description**: The system must provide visibility into its operations.
**Attributes**:
- Comprehensive logging via loguru
- Performance metrics tracked
- Error conditions logged with context
- Decision reasoning captured

### QA3: Extensibility
**ID**: QA-EXT-001
**Description**: The system must be extensible for future enhancements.
**Attributes**:
- New performance metrics can be added
- Additional AI models can be integrated
- New report formats can be supported
- Additional variant types can be added