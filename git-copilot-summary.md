# MASTER CODEBASE STUDY + EXPLANATION PROMPT

```text

You are now acting as BOTH:

1. A senior software/ML engineer auditing this existing project.
2. A technical professor teaching me this project from zero.

Your task is NOT to modify the project initially.

Your first responsibility is to deeply inspect and understand the EXISTING CODEBASE and then produce a complete technical explanation of how the system works.

============================================================
IMPORTANT PROJECT CONTEXT
============================================================

This is an existing healthcare claims intelligence / data-quality / anomaly-detection / risk-analysis platform.

The repository contains major areas including:

- Backend API
- Data ingestion
- Data engineering
- Data cleaning
- Data profiling
- Data quality
- Historical baselines
- Feature engineering
- Feature selection
- Anomaly detection
- Risk modelling
- LLM-assisted investigation
- Incident management
- Human-in-the-loop workflows
- Remediation
- Revalidation
- Audit/history
- Simulation/demo pipeline
- React frontend
- ML model artifacts
- Generated datasets
- Reports
- Automated tests

The repository must be treated as an EXISTING SYSTEM.

DO NOT redesign it.
DO NOT rewrite it.
DO NOT assume that a file is implemented merely because the file exists.
DO NOT assume that a function works merely because it has a reasonable name.

============================================================
CORE RULE: SOURCE CODE IS THE AUTHORITY
============================================================

You MUST inspect the actual source code before explaining implementation details.

Never explain a function merely from its filename.
Never invent formulas.
Never invent algorithms.
Never claim that a library is being used unless you verify it from imports, requirements, package files, configuration, actual code, build configuration, or dependency files.
Never claim that a formula is implemented unless you locate where it is implemented.
Never claim that an algorithm is actually used in production/inference merely because its module exists.

Distinguish clearly between:

1. IMPLEMENTED
2. CALLED / WIRED INTO PIPELINE
3. TESTED
4. GENERATED ARTIFACT
5. PRESENT BUT NOT VERIFIED
6. MOCK / DEMO
7. TODO / INCOMPLETE

If something cannot be verified from the source code, explicitly write:

"NOT VERIFIED FROM SOURCE"

Do NOT fill that gap using assumptions.

============================================================
PRIMARY OBJECTIVE
============================================================

Teach me the ENTIRE project in simple English while maintaining full technical depth.

I need to understand:

- what the project does
- why it exists
- how every major subsystem works
- how the code implements the theory
- what libraries are used
- what algorithms are used
- what formulas are used
- where each concept exists in the code
- how data flows through the system
- how the AI/ML components work
- how the simulation works
- how the frontend works
- how the backend works
- how everything connects
- why each technology/algorithm was selected
- what happens to a single claim as it travels through the system

The final explanation must be useful for BOTH:

A. Understanding the project deeply.
B. Explaining the project confidently during a viva/project presentation.

============================================================
PHASE 0 - CODEBASE DISCOVERY
============================================================

Before writing the explanation, inspect the repository.

First determine:

1. Root directory structure
2. Backend structure
3. Frontend structure
4. Data structure
5. Model/artifact structure
6. Test structure
7. Configuration files
8. Dependency files
9. Environment files
10. Documentation
11. Scripts
12. Entry points
13. API routers
14. Database layer
15. ML pipelines
16. Simulation pipeline

Search the repository systematically.
Inspect relevant source files.
Inspect relevant tests.
Inspect configuration.
Inspect dependency declarations.

Do NOT immediately start explaining after seeing the directory tree.
First understand the actual implementation.

============================================================
PHASE 1 - CREATE A CODEBASE MAP
============================================================

Create a complete map in this format:

------------------------------------------------------------
COMPONENT
------------------------------------------------------------

Name:
Purpose:
Technology:
Location:
Entry point:
Important files:
Important classes:
Important functions:
Inputs:
Outputs:
Dependencies:
Called by:
Calls:
Tests:
Artifacts:
Status:

------------------------------------------------------------

For example:

Concept:
Isolation Forest anomaly detection

Theory:
...

Algorithm:
...

Implementation file:
app/anomaly/isolation_forest.py

Class/function:
<actual discovered class/function>

Used by:
<actual caller>

Input:
<actual input>

Output:
<actual output>

Formula:
<actual formula if implemented>

Tests:
<actual tests>

Status:
IMPLEMENTED / WIRED / TESTED / NOT VERIFIED

Do this for EVERY major subsystem.

============================================================
PHASE 2 - PROJECT EXPLANATION IN SIMPLE ENGLISH
============================================================

Start the final explanation with:

"THE PROJECT IN ONE SIMPLE STORY"

Explain the project as if I know basic programming but do not know this architecture.
Use real-world examples.

For example:

Imagine a hospital sends thousands of claims.
The system receives them.
It checks whether the data is complete.
It checks whether values are valid.
It compares current behaviour with historical behaviour.
It generates useful features.
It searches for unusual claims.
It estimates risk.
It creates an investigation context.
An LLM helps explain the evidence.
A human reviews the result.
The system can remediate the problem.
Then it checks whether the problem was actually fixed.
Finally, everything is recorded for auditing.

Then map that story directly to the actual code.

============================================================
PHASE 3 - COMPLETE TECHNOLOGY STACK
============================================================

Create a complete technology stack table.

Columns:

Technology / Library
Purpose
Where Used
Why Used
Important Files
Status

Include, if actually present:

- Python
- FastAPI
- Pydantic
- pandas
- NumPy
- scikit-learn
- XGBoost
- SciPy
- Great Expectations
- joblib/pickle
- Mistral / LLM client
- React
- TypeScript
- Vite
- charting libraries
- CSS/UI libraries
- database libraries
- SQLAlchemy
- Alembic
- HTTP clients
- pytest
- coverage
- linting tools
- build tools

BUT:

Only list a technology if it is actually verified from the repository.

If a technology is expected but not found:

"Not verified from source."

============================================================
PHASE 4 - COMPLETE CODEBASE STRUCTURE
============================================================

Explain the repository folder-by-folder.

For each major folder:

1. What it contains
2. Why it exists
3. How it connects to the rest
4. Important files
5. Important classes/functions
6. Example execution path

Do NOT simply repeat the directory tree.
Explain the architectural responsibility.

============================================================
PHASE 5 - BACKEND ARCHITECTURE
============================================================

Explain the backend deeply.

Cover:

- Application entry point
- FastAPI
- Routers
- Services
- Schemas
- Models
- Database
- Configuration
- Logging
- Error handling
- Dependency injection if present
- Request lifecycle
- Response lifecycle

Explain:

CLIENT
-> API ROUTER
-> SCHEMA VALIDATION
-> SERVICE
-> BUSINESS LOGIC
-> MODEL / DATABASE / PIPELINE
-> RESPONSE
-> CLIENT

For every stage:

- explain theory
- show actual code
- give file pointer
- give function/class pointer
- explain inputs
- explain outputs

============================================================
PHASE 6 - DATA ENGINEERING
============================================================

Explain the complete data engineering pipeline.

Cover:

- ingestion
- loading
- profiling
- sampling
- type conversion
- standardization
- date standardization
- categorization
- invalid-value detection
- duplicate detection
- cleaning
- quality issue logging
- report generation

For each component explain:

WHY IT EXISTS
WHAT PROBLEM IT SOLVES
HOW IT WORKS
ALGORITHM / LOGIC
FORMULA IF ANY
ACTUAL CODE LOCATION
ACTUAL FUNCTION / CLASS
INPUT
OUTPUT
NEXT STEP
TEST

============================================================
PHASE 7 - DATA QUALITY
============================================================

Explain data quality from first principles.

Explain:

What is data quality?
Why does healthcare claims data require quality checks?

Then explain every quality dimension actually implemented.

For example, if present:

- completeness
- freshness
- uniqueness
- validity
- range checks

For each:

1. Simple-English definition
2. Real-world example
3. Mathematical definition if applicable
4. Formula
5. Actual implementation
6. Code pointer
7. Input
8. Output
9. How score is calculated
10. How the score is used later

============================================================
PHASE 8 - BASELINES
============================================================

Explain baseline theory from zero.

Explain:

What is a baseline?
Why do we need historical behaviour?

Difference between:

NORMAL VALUE
and
ANOMALOUS VALUE

Explain every baseline implemented.

For each baseline:

- purpose
- historical data
- window
- statistic
- formula
- implementation
- code location
- example
- output
- downstream usage

Explain baseline snapshots and historical comparison.

============================================================
PHASE 9 - FEATURE ENGINEERING
============================================================

Explain feature engineering deeply.

Start with:

"What is a feature?"

Then explain every implemented feature.

For each:

Feature name:
Business meaning:
Mathematical meaning:
Formula:
Input columns:
Output:
File:
Function:
Why useful for ML:
Example:

Cover actual implemented areas such as:

- amount ratios
- categorical encoding
- date features
- length of stay
- provider frequency
- window aggregates
- deviation features

Only include what is actually present.

============================================================
PHASE 10 - FEATURE SELECTION
============================================================

Explain the entire feature-selection pipeline.

Especially:

Stage 1 - Structural
Stage 2 - Statistical
Stage 3 - Model-based

Explain:

Why feature selection matters.
What happens at each stage.
What causes a feature to be removed.
How temporal splitting works.
Why leakage matters.
Explain every formula actually used.
Point to the exact implementation.

============================================================
PHASE 11 - AI/ML - COMPLETE DEEP DIVE
============================================================

This section is extremely important.

Divide it into:

A. Statistical foundations
B. Unsupervised anomaly detection
C. Supervised risk prediction
D. Feature engineering
E. Feature selection
F. Model benchmarking
G. Model calibration
H. LLM investigation
I. Human-in-the-loop AI
J. False positives and false negatives
K. Why each model exists
L. How the AI components interact

============================================================
A - STATISTICAL FOUNDATIONS
============================================================

Explain every statistical concept actually used.

For each:

Simple English
Theory
Formula
Example
Code implementation
File pointer
Function
Purpose in this project

Examples may include:

- mean
- median
- quartiles
- IQR
- percentile
- standard deviation
- distributions
- thresholds
- scaling

ONLY if actually used.

============================================================
B - UNSUPERVISED ANOMALY DETECTION
============================================================

Explain every implemented anomaly algorithm separately.

Potential examples:

- IQR
- Isolation Forest
- Local Outlier Factor
- HBOS

For EACH algorithm:

1. What is anomaly detection?
2. Why is this algorithm useful?
3. How the algorithm works conceptually
4. Step-by-step algorithm
5. Mathematical foundation
6. Formula
7. Meaning of every variable
8. Tiny numerical example
9. Actual implementation
10. Exact file
11. Exact class/function
12. Input
13. Output
14. How its output is normalized/scored
15. How model selection uses it
16. How benchmark evaluates it
17. How tests validate it
18. Limitations
19. Why this project uses it

For Isolation Forest specifically, explain the path-length concept and anomaly scoring if actually implemented.

For LOF, explain local density and relative density if actually implemented.

For HBOS, explain histogram-based density estimation if actually implemented.

For IQR, explain:

Q1
Q3
IQR = Q3 - Q1

and outlier boundaries if implemented.

Do not merely describe scikit-learn.
Explain what OUR CODE does with the algorithm.

============================================================
C - SUPERVISED RISK PREDICTION
============================================================

Explain every implemented risk model.

Potential models:

- Logistic Regression
- Random Forest
- XGBoost

For each:

1. What problem it solves
2. Difference from anomaly detection
3. Input features
4. Target label
5. Training process
6. Prediction
7. Probability
8. Score
9. Calibration
10. Benchmarking
11. Model selection
12. Saved artifact
13. Inference
14. Actual code location

Explain mathematical theory.

For Logistic Regression, explain sigmoid if actually used:

sigmoid(z) = 1 / (1 + e^-z)

Then explain:

z = w0 + w1*x1 + ... + wm*xm

ONLY if this corresponds to the actual implementation/theory being used.

For Random Forest explain:

- decision trees
- bootstrapping
- random feature selection
- ensemble voting

For XGBoost explain:

- boosting
- sequential trees
- residual/error correction
- learning rate
- tree contribution

Do not claim custom implementations if the project uses libraries.
Explain what the library does versus what OUR CODE does.

============================================================
D - FEATURE ENGINEERING FOR ML
============================================================

Explain how raw claims become model-ready data.

Trace:

RAW COLUMN
-> CLEANING
-> TRANSFORMATION
-> FEATURE
-> FEATURE SELECTION
-> MODEL INPUT

Use actual columns from the repository where available.

============================================================
E - FEATURE SELECTION
============================================================

Explain why unnecessary features can hurt models.
Explain every implemented stage.

Show:

Raw feature set
-> Stage 1
-> Remaining features
-> Stage 2
-> Remaining features
-> Stage 3
-> Final selected features

Point to the actual code.

============================================================
F - MODEL BENCHMARKING
============================================================

Explain why multiple algorithms are benchmarked.
Explain every metric actually used.

Potential metrics include:

- accuracy
- precision
- recall
- F1
- ROC-AUC
- PR-AUC
- confusion matrix

Only explain metrics verified in code.

For every metric:

Formula
Simple meaning
Example
Where calculated
How used to select models

============================================================
G - CALIBRATION
============================================================

Explain model calibration from zero.

Explain:

Prediction probability
vs
actual probability

Explain the calibration method actually used.
Point to exact code.

============================================================
H - LLM INVESTIGATION
============================================================

Explain the LLM subsystem in depth.

Trace:

Incident
-> Investigation request
-> Payload builder
-> Prompt template
-> Mistral/LLM client
-> Model response
-> Response parser
-> Investigation result
-> Investigation log

Explain:

- why an LLM is used
- what information is given to it
- how prompts are constructed
- what the payload contains
- how the response is parsed
- how structured output is produced
- what errors can occur
- how investigations are logged
- what the LLM should NOT be trusted to do

Distinguish:

DETERMINISTIC ML
vs
GENERATIVE AI

Explain exactly where each is used.

============================================================
I - HUMAN-IN-THE-LOOP
============================================================

Explain why HITL exists.

Trace:

AI result
-> Investigator
-> Accept / Reject
-> State transition
-> Recalculation if needed
-> Audit

Explain every state and transition actually implemented.

============================================================
J - FALSE POSITIVES / FALSE NEGATIVES
============================================================

Explain:

False positive:
system says abnormal but it is normal.

False negative:
system misses a real problem.

Explain why this matters in healthcare claims.
Show where the project attempts to control this.

============================================================
K - WHY EACH MODEL EXISTS
============================================================

Create a comparison table:

Model
Type
Purpose
Input
Output
Strength
Weakness
Why useful here
Where implemented

============================================================
L - HOW ALL AI COMPONENTS CONNECT
============================================================

Create one complete AI pipeline:

Data
-> Quality
-> Baseline
-> Features
-> Anomaly detection
-> Risk model
-> Priority/severity
-> LLM investigation
-> Human decision
-> Remediation
-> Revalidation

Explain every arrow.

============================================================
PHASE 12 - RISK SCORING
============================================================

Explain:

- business impact
- percentile scaling
- severity
- priority
- weight configuration

For every scoring formula:

1. Formula
2. Meaning of each variable
3. Example
4. Actual implementation
5. File
6. Function
7. Output

If formulas are composed:
Show the full chain.

For example:

Raw metric
-> normalized metric
-> severity
-> business impact
-> priority

Do not invent formulas.

============================================================
PHASE 13 - INCIDENT MANAGEMENT
============================================================

Explain:

What is an incident?
How is an incident created?
What information does it contain?
How does an anomaly/risk result become an incident?

Trace actual code.

Explain:

router
schema
model
service
database/artifact
frontend

============================================================
PHASE 14 - REMEDIATION
============================================================

Explain remediation in depth.
Cover every actual handler.

Potential areas:

- duplicate handling
- imputation
- manual remediation
- status mapping

Explain:

Issue
-> Rule
-> Handler
-> Change
-> Result
-> Log

Explain configuration YAML files.
Explain precedence rules if present.

============================================================
PHASE 15 - REVALIDATION
============================================================

Explain why remediation cannot simply be assumed successful.

Trace:

Before
-> Remediation
-> Recompute
-> Comparison
-> Resolution criteria
-> Resolved / unresolved

Explain every implemented comparison and criterion.

============================================================
PHASE 16 - AUDIT / HISTORY
============================================================

Explain:

- audit trail
- provenance
- history
- registry
- deterministic ordering
- aggregation

Explain why auditability is important.
Trace actual data through the audit subsystem.

============================================================
PHASE 17 - SIMULATION - VERY DEEP
============================================================

This section must be extremely detailed.
Do not just explain what the simulator is.
Explain exactly how it executes.

Start by identifying:

- simulator entry point
- batch generation
- data generator
- anomaly runner
- quality runner
- pipeline
- risk model
- narrative
- upload
- router
- window processor
- frontend simulator

Then construct a complete execution story.

Use:

BATCH 1
-> BATCH 2
-> BATCH 3
...

if the code actually uses sequential batches.

Explain:

1. How a batch is created.
2. What data is generated.
3. How records are structured.
4. How synthetic anomalies are introduced.
5. How ground truth is maintained.
6. How the batch enters the pipeline.
7. How profiling occurs.
8. How quality is calculated.
9. How anomalies are detected.
10. How risk is calculated.
11. How incidents are produced.
12. How narratives are created.
13. How results are stored.
14. How frontend receives them.
15. How charts update.
16. How live simulation works.

For every step provide:

THEORY
-> ACTUAL FILE
-> FUNCTION
-> INPUT
-> PROCESS
-> OUTPUT
-> NEXT FUNCTION

============================================================
SIMULATION EXAMPLE
============================================================

Construct ONE complete fictional claim/batch example.

Example:

A claim has:

patient ID
provider
claim amount
admission date
discharge date
diagnosis
etc.

Then show exactly what happens to it.

Example:

Raw claim
-> Cleaned claim
-> Quality checks
-> Feature generation
-> Anomaly score
-> Risk score
-> Priority
-> Incident
-> Investigation
-> Human decision
-> Remediation
-> Revalidation

Use actual project fields where available.
Clearly mark any example values that are illustrative.

============================================================
PHASE 18 - FRONTEND
============================================================

Explain the frontend from zero.

Cover:

- React
- TypeScript
- Vite
- App entry
- routing
- layouts
- pages
- reusable UI components
- hooks
- services
- types
- data
- charts
- API communication
- live stream
- loading
- error states

Explain every major page:

Dashboard
History
Incidents
Investigation
Live Monitor
Settings
Simulator
Upload

For each page:

Purpose
Entry point
Components
Data source
API/service
State
User interaction
Backend dependency
Output

============================================================
FRONTEND -> BACKEND TRACE
============================================================

For important features show:

USER ACTION
-> REACT COMPONENT
-> HOOK
-> SERVICE
-> HTTP REQUEST
-> FASTAPI ROUTER
-> SCHEMA
-> SERVICE
-> MODEL/DATA
-> RESPONSE
-> REACT STATE
-> UI UPDATE

Use actual filenames and functions.

============================================================
PHASE 19 - FORMULAS MASTER INDEX
============================================================

Create a complete formula reference.

Columns:

Formula
Meaning
Variables
Used For
File
Function
Example

Only include formulas actually present or directly required by implemented algorithms.

Separate:

1. Data quality formulas
2. Baseline formulas
3. Feature formulas
4. Anomaly formulas
5. Risk formulas
6. Evaluation formulas
7. Scoring formulas
8. Other statistical formulas

============================================================
PHASE 20 - ALGORITHM MASTER INDEX
============================================================

Create:

Algorithm
Type
Purpose
Input
Output
Formula
Implementation file
Function/class
Library
Training required?
Used in production pipeline?
Tested?
Status

============================================================
PHASE 21 - LIBRARY MASTER INDEX
============================================================

Create:

Library
Version
Purpose
Imported in
Used by
Why required
Alternative
Status

Do not guess versions.
Read dependency files.

============================================================
PHASE 22 - COMPLETE EXECUTION FLOW
============================================================

Create the complete system execution flow.

Start with:

USER / DATA SOURCE

Then show every major stage.

Example:

Upload
-> Ingestion
-> Profiling
-> Cleaning
-> Quality
-> Baseline
-> Features
-> Anomaly
-> Risk
-> Incident
-> LLM
-> HITL
-> Remediation
-> Revalidation
-> Audit
-> Dashboard

For EVERY arrow explain:

"What happens here?"
"Which file performs it?"
"Which function performs it?"
"What data is passed?"
"What is returned?"

============================================================
PHASE 23 - COMPLETE SINGLE-CLAIM WALKTHROUGH
============================================================

Take ONE representative claim and follow it through the entire system.

At each stage show:

Input
Transformation
Output
File
Function

This must be understandable to someone with basic programming knowledge.

============================================================
PHASE 24 - IMPLEMENTATION STATUS
============================================================

Create a table:

Component
Implemented?
Wired?
Tested?
Frontend connected?
Production-ready?
Evidence
Notes

Use only evidence from the repository.
Do not claim completion merely from filenames.

============================================================
PHASE 25 - TEST COVERAGE
============================================================

Map tests to functionality.

Create:

Feature
Test file
What it tests
Status
Potential missing coverage

Identify gaps.
Do not say tests pass unless you actually ran them.

============================================================
PHASE 26 - CODE POINTER SYSTEM
============================================================

Every important technical concept MUST have a pointer.

Use this format:

[CODE POINTER]

Concept:
<concept>

File:
<relative path>

Class:
<actual class or N/A>

Function:
<actual function or N/A>

Relevant code:
<small relevant code snippet>

Called from:
<actual caller>

Calls:
<actual downstream function>

Purpose:
<simple explanation>

Do this throughout the document.
Do not dump entire files.
Only show the smallest useful code snippet.

============================================================
PHASE 27 - THEORY -> CODE MAPPING
============================================================

For every major concept create:

THEORY
-> MATHEMATICS
-> ALGORITHM
-> LIBRARY
-> PROJECT CODE
-> INPUT
-> OUTPUT
-> NEXT STAGE

This mapping is extremely important.

============================================================
PHASE 28 - SIMPLE ENGLISH REQUIREMENT
============================================================

Always explain difficult terminology immediately.

Example:

Instead of:

"Isolation Forest exploits path-length-based partitioning."

Write:

"Isolation Forest tries to separate unusual records from normal records. An unusual record is usually easier to isolate, so it tends to require fewer random splits. The number of splits is called the path length."

Then give the technical explanation.

Use:

SIMPLE EXPLANATION
then:
TECHNICAL EXPLANATION
then:
CODE IMPLEMENTATION

============================================================
PHASE 29 - VIVA PREPARATION
============================================================

At the end create a complete viva preparation section.

Include:

### Basic questions

- What is the project?
- Why was it created?
- What problem does it solve?
- What is the architecture?
- What technologies are used?

### Data engineering questions

- What is profiling?
- What is cleaning?
- Why detect duplicates?
- What is data quality?
- What is a baseline?

### ML questions

- What is anomaly detection?
- Why use unsupervised learning?
- Why Isolation Forest?
- What is LOF?
- What is HBOS?
- What is IQR?
- Difference between anomaly detection and classification?
- Why Random Forest?
- Why XGBoost?
- What is Logistic Regression?
- What is feature engineering?
- What is feature selection?
- What is data leakage?
- What is temporal leakage?
- What is calibration?
- What is precision?
- What is recall?
- What is F1?
- What is ROC-AUC?

### AI questions

- Why use an LLM?
- Why use an LLM after ML?
- What does the LLM receive?
- How are prompts constructed?
- Can the LLM be trusted?
- How do you prevent hallucination?
- What is human-in-the-loop?

### Simulation questions

- Why is simulation required?
- How is synthetic data generated?
- How are anomalies introduced?
- What is ground truth?
- How does a batch move through the pipeline?
- How does the frontend receive simulation results?

### Architecture questions

- Why FastAPI?
- Why React?
- Why TypeScript?
- Why separate routers and services?
- Why use schemas?
- Why maintain audit history?
- Why have remediation and revalidation separately?

For every viva question provide:

SHORT ANSWER
then:
DETAILED ANSWER
then:
CODE POINTER

============================================================
PHASE 30 - EXPLAIN THIS TO THE PANEL
============================================================

Create presentation-ready explanations.

For every major component give me a 30-second answer.
Then a 1-minute answer.
Then a 3-minute deep answer.

Example:

"Explain Isolation Forest."

30-second answer:
...

1-minute answer:
...

3-minute answer:
...

Code pointer:
...

============================================================
PHASE 31 - DO NOT HALLUCINATE
============================================================

This is mandatory.

If source code does not prove something:

Say:

"NOT VERIFIED FROM SOURCE."

If theory is required to explain an implemented library algorithm, separate it as:

"THEORETICAL BACKGROUND"

Do not imply that the project manually implements the algorithm if a library does it.

Distinguish:

LIBRARY IMPLEMENTATION
from:
OUR PROJECT LOGIC AROUND THE LIBRARY.

============================================================
PHASE 32 - DO NOT MODIFY CODE DURING INITIAL STUDY
============================================================

For this task, DO NOT change source code.

DO NOT refactor.
DO NOT rename.
DO NOT delete.
DO NOT create new implementation files.
DO NOT "fix" issues.

First produce the study/documentation.

If you discover a bug, document it under:

KNOWN ISSUE

rather than silently fixing it.

============================================================
PHASE 33 - FINAL OUTPUT STRUCTURE
============================================================

Your final documentation MUST contain:

# 1. Project in One Simple Story
# 2. Problem Statement
# 3. Project Objectives
# 4. Complete Architecture
# 5. Complete Repository Map
# 6. Technology Stack
# 7. Libraries
# 8. Backend Architecture
# 9. Data Engineering
# 10. Data Quality
# 11. Baselines
# 12. Feature Engineering
# 13. Feature Selection
# 14. Anomaly Detection
# 15. Risk Modelling
# 16. Model Benchmarking
# 17. Model Calibration
# 18. Risk / Severity / Priority Scoring
# 19. LLM Investigation
# 20. Human-in-the-Loop
# 21. Incident Management
# 22. Remediation
# 23. Revalidation
# 24. Audit / History
# 25. Simulation - Deep Dive
# 26. Frontend
# 27. Frontend <-> Backend Flow
# 28. Complete End-to-End Pipeline
# 29. Single Claim Walkthrough
# 30. Formula Master Index
# 31. Algorithm Master Index
# 32. Library Master Index
# 33. Code Pointer Index
# 34. Test Coverage
# 35. Implementation Status
# 36. Known Issues
# 37. Architecture Strengths
# 38. Architecture Weaknesses
# 39. What Remains To Be Implemented
# 40. Viva Questions and Answers
# 41. Presentation-Ready Explanations
# 42. Final One-Page Project Explanation

============================================================
FINAL ONE-PAGE EXPLANATION
============================================================

End with a concise explanation I can memorize before a presentation.

It should answer:

"What did you build?"
"How does it work?"
"What technologies did you use?"
"What ML algorithms did you use?"
"Why those algorithms?"
"Where is AI used?"
"How does simulation work?"
"How does the system handle human decisions?"
"What happens after remediation?"
"What makes this project different?"

Keep this final section simple enough to memorize.

============================================================
QUALITY STANDARD
============================================================

The final output must be:

- technically accurate
- based on actual source code
- extremely detailed
- simple English
- structured
- traceable
- suitable for learning
- suitable for viva
- suitable for project documentation

Do NOT produce a generic textbook explanation.
This must be an explanation of THIS SPECIFIC CODEBASE.

Whenever possible use:

PROJECT THEORY
+
ACTUAL FORMULA
+
ACTUAL CODE
+
ACTUAL FILE PATH
+
ACTUAL FUNCTION
+
ACTUAL DATA FLOW

That combination is mandatory.

============================================================
IMPORTANT EXECUTION INSTRUCTION
============================================================

DO NOT start by generating the final explanation immediately.

First perform a READ-ONLY CODEBASE AUDIT.

After the audit, give me:

1. Repository understanding
2. Identified architecture
3. Major modules discovered
4. Algorithms discovered
5. Libraries discovered
6. Data flow discovered
7. Simulation flow discovered
8. ML pipeline discovered
9. Areas that require deeper source inspection
10. Any ambiguities or missing source information

Then proceed to generate the complete documentation.

If the repository is too large to inspect in one pass:

Work systematically by subsystem.
Do NOT guess the remaining parts.

============================================================
MOST IMPORTANT PRINCIPLE
============================================================

You are not documenting filenames.
You are reconstructing HOW THE SYSTEM ACTUALLY WORKS.

Always answer:

WHY?
WHAT?
HOW?
WHERE?
WHEN?
INPUT?
OUTPUT?
FORMULA?
CODE?
NEXT STEP?

And always connect:

THEORY -> CODE -> DATA -> OUTPUT -> NEXT STAGE.

============================================================
END OF MASTER PROMPT
============================================================

Additional instruction:

Keep all mathematical and ML formulas in plain text notation. Do not use pictorial representations, rendered equation images, or image-style formula diagrams. For example:

MissingRate = (missing_cells / total_cells) * 100
DuplicateRate = (duplicate_rows / total_rows) * 100
score = SUM(weight[type] * average_band_score[type])

Use text arrows such as `->` when showing data flow.
```
