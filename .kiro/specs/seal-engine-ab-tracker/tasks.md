# Tasks: SEAL Engine & A/B Tracker Implementation

## Overview

Implementation tasks for creating the SEAL engine and A/B tracker functionality as specified in the design and requirements documents.

## Task List

### T1: Project Setup and Configuration
**ID**: T1
**Description**: Set up the project structure and verify dependencies.
**Subtasks**:
- T1.1: Verify Python environment and dependencies
- T1.2: Check database schema and connectivity
- T1.3: Configure OpenAI API credentials
- T1.4: Test Obsidian bridge connectivity

**Acceptance Criteria**:
- Python 3.8+ environment confirmed
- Database `red.db` exists with required tables
- OpenAI API key configured in environment
- Obsidian bridge responds to test requests

### T2: Implement SEAL Engine Core Function
**ID**: T2
**Description**: Implement the main `run_seal_cycle()` function in `seal_engine.py`.
**Subtasks**:
- T2.1: Create `seal_engine.py` with imports and constants
- T2.2: Implement database connection with `DB_PATH = r"E:\RED\red.db"`
- T2.3: Define `SEALResult` type structure
- T2.4: Implement function skeleton with proper return type

**Acceptance Criteria**:
- File created at `E:\RED\06_seal\seal_engine.py`
- Imports include: `sys`, `sqlite3`, `datetime`, `openai`, `loguru`, `config`
- Function signature: `def run_seal_cycle() -> dict`
- Returns dictionary with expected keys

### T3: Implement Campaign Performance Analysis
**ID**: T3
**Description**: Implement the ANALYSIS PHASE of SEAL engine.
**Subtasks**:
- T3.1: Write SQL query to get campaign performance by category/variant
- T3.2: Calculate open_rate, click_rate, reply_rate
- T3.3: Filter campaigns with open_rate < 0.20 as low performers
- T3.4: Log analysis results using loguru

**Acceptance Criteria**:
- Query returns performance data grouped by `categoria` and `variant`
- Rates calculated correctly: `open_rate = opens/total_sent`
- Low performers identified with threshold 0.20
- Analysis logged with appropriate detail level

### T4: Implement AI Improvement Generation
**ID**: T4
**Description**: Implement the IMPROVEMENT PHASE of SEAL engine using OpenAI.
**Subtasks**:
- T4.1: Configure OpenAI client with `config.Config.llm_base_url`
- T4.2: Create prompt engineering for email subject improvement
- T4.3: Generate improved subject lines for low performers
- T4.4: Save suggestions to `seal_insights` table

**Acceptance Criteria**:
- OpenAI API called with appropriate parameters
- Suggestions include original, improved subject, rationale, confidence
- Suggestions saved to database with `applied=0` flag
- API failures handled gracefully with fallback

### T5: Implement Report Generation and Logging
**ID**: T5
**Description**: Implement the LOGGING PHASE of SEAL engine.
**Subtasks**:
- T5.1: Generate markdown report with analysis summary
- T5.2: Write report to Obsidian via `obsidian_bridge.escribir_seal_log()`
- T5.3: Implement fallback to `logs\seal_{today}.md` if Obsidian unavailable
- T5.4: Return complete `SEALResult` dictionary

**Acceptance Criteria**:
- Markdown report includes date, analyzed campaigns, low performers, suggestions
- Report written to `04_seal_logs/seal_{today}.md` in Obsidian
- Fallback to local `logs` directory if Obsidian bridge fails
- `SEALResult` includes all required summary statistics

### T6: Implement A/B Tracker Core Function
**ID**: T6
**Description**: Implement the `get_variant()` function in `ab_tracker.py`.
**Subtasks**:
- T6.1: Create `ab_tracker.py` with imports and constants
- T6.2: Implement database connection with same `DB_PATH`
- T6.3: Define function signature: `def get_variant(lead_id: int, categoria: str) -> str`
- T6.4: Implement basic return logic

**Acceptance Criteria**:
- File created at `E:\RED\06_seal\ab_tracker.py`
- Imports include: `sys`, `sqlite3`, `random`
- Function returns "A" or "B" string
- Input validation for `lead_id` and `categoria`

### T7: Implement Variant Performance Query
**ID**: T7
**Description**: Implement performance data querying for A/B tracker.
**Subtasks**:
- T7.1: Query `ab_experiments` table for variant performance
- T7.2: Calculate performance scores for variants A and B
- T7.3: Determine if sufficient data exists (<10 sends per variant)
- T7.4: Log performance data for debugging

**Acceptance Criteria**:
- Query returns performance data for given `categoria`
- Scores calculated using weighted metrics (open:0.5, click:0.3, reply:0.2)
- Insufficient data threshold: <10 sends per variant
- Performance data logged for analytics

### T8: Implement Decision Logic
**ID**: T8
**Description**: Implement the decision logic for variant selection.
**Subtasks**:
- T8.1: Implement random fallback for insufficient data (seeded by `lead_id`)
- T8.2: Implement performance-based selection when both variants present
- T8.3: Implement fallback to available variant when only one exists
- T8.4: Implement default "A" when no data exists

**Acceptance Criteria**:
- Random selection uses `random.seed(lead_id)` for determinism
- Better performing variant selected when data sufficient
- Decision reason logged with appropriate code
- Function deterministic for same inputs

### T9: Implement Error Handling and Resilience
**ID**: T9
**Description**: Implement comprehensive error handling for both modules.
**Subtasks**:
- T9.1: Database connection error handling with retry logic
- T9.2: OpenAI API error handling with exponential backoff
- T9.3: Obsidian bridge error handling with fallback logging
- T9.4: Input validation and sanitization

**Acceptance Criteria**:
- Database errors trigger retry (max 3 attempts)
- OpenAI failures skip suggestions but continue analysis
- Obsidian failures use local log directory fallback
- SQL queries use parameterized statements

### T10: Update Module Initialization
**ID**: T10
**Description**: Update the `__init__.py` file to expose public functions.
**Subtasks**:
- T10.1: Update `06_seal/__init__.py` to import new modules
- T10.2: Expose `run_seal_cycle` and `get_variant` functions
- T10.3: Add module documentation
- T10.4: Verify import works correctly

**Acceptance Criteria**:
- `from 06_seal import run_seal_cycle, get_variant` works
- Module has basic documentation
- All public functions accessible
- No circular import issues

### T11: Write Unit Tests
**ID**: T11
**Description**: Create comprehensive unit tests for both modules.
**Subtasks**:
- T11.1: Create test file for `seal_engine.py`
- T11.2: Test database query and analysis logic
- T11.3: Create test file for `ab_tracker.py`
- T11.4: Test variant selection logic with mock data

**Acceptance Criteria**:
- Tests cover all major functions
- Mock database for isolated testing
- Mock OpenAI API to avoid actual calls
- Test edge cases and error scenarios

### T12: Write Property-Based Tests
**ID**: T12
**Description**: Create property-based tests using Hypothesis library.
**Subtasks**:
- T12.1: Install and configure Hypothesis library
- T12.2: Write property test for `get_variant()` determinism
- T12.3: Write property test for SEAL result structure
- T12.4: Write property test for performance score bounds

**Acceptance Criteria**:
- Hypothesis generates diverse test cases
- Properties verify correctness invariants
- Tests run within reasonable time
- Edge cases automatically discovered

### T13: Integration Testing
**ID**: T13
**Description**: Test complete integration with existing system.
**Subtasks**:
- T13.1: Test SEAL engine with actual database
- T13.2: Test A/B tracker with campaign data
- T13.3: Test Obsidian bridge integration
- T13.4: Test error recovery scenarios

**Acceptance Criteria**:
- SEAL cycle completes successfully
- A/B tracker returns valid variants
- Reports created in correct locations
- Error handling works as designed

### T14: Performance Optimization
**ID**: T14
**Description**: Optimize performance for production use.
**Subtasks**:
- T14.1: Add database query indexing for performance
- T14.2: Implement batch processing for large datasets
- T14.3: Add caching for frequently accessed data
- T14.4: Monitor memory usage and optimize

**Acceptance Criteria**:
- SEAL cycle completes within 5 minutes for 1000 campaigns
- Database queries use appropriate indexes
- Memory usage stays under 500MB
- Batch processing prevents timeouts

### T15: Documentation and Examples
**ID**: T15
**Description**: Create comprehensive documentation and usage examples.
**Subtasks**:
- T15.1: Write module docstrings with examples
- T15.2: Create README with usage instructions
- T15.3: Add example scripts demonstrating functionality
- T15.4: Document configuration requirements

**Acceptance Criteria**:
- All functions have complete docstrings
- README explains how to use both modules
- Examples show common use cases
- Configuration instructions clear and complete

## Implementation Notes

### Database Schema Reference
- Use existing tables: `campaigns`, `ab_experiments`, `seal_insights`
- Foreign key relationships must be respected
- Field names and types as defined in `db.py`

### Configuration
- OpenAI: `Config.llm_base_url`, `Config.llm_model`
- Obsidian: `Config.obsidian_url`, `Config.obsidian_api_key`
- Database: Hardcoded `r"E:\RED\red.db"`

### Error Handling Patterns
- Database errors: `sqlite3.Error` with retry logic
- API errors: Appropriate exception with fallback
- Validation errors: `ValueError` with descriptive message
- All errors logged via `loguru`

### Testing Strategy
- Unit tests with mocked dependencies
- Property-based tests with Hypothesis
- Integration tests with actual components
- Performance tests with large datasets

### Code Quality Standards
- Type hints for all functions
- Docstrings with parameter descriptions
- Consistent error handling
- Follow existing project conventions