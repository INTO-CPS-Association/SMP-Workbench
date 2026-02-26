# Test List
This is the complete list of tests in the project. The tests will be categorized into different sections with respect to the subsystem that they test. There are both positive and negative tests.

## Subsystem: File Management
### JsonFileReadingStrategy
File: json_file_reading_strategy_test.py
#### Positive tests:
- [OK] Test that the read method in JsonFileReadingStrategy returns an instance of a JsonFileWrapper class.
#### Negative tests:
- [OK] Test that the read method in JsonFileReadingStrategy raises an OSError exception when the given path to the file does not end with '.json'
    - [OK] Test that the OSError exception contains a value="File did not end with .json".

## SubSystem: Log Parsing
### JsonLogParsingStrategy
File: json_log_parsing_strategy_test.py
#### Positive tests:
- [OK] Test that the createLogFile method in JsonLogParsingStrategy returns a LogFile with the correct set of states
#### Negative tests:
- NIL

## SubSystem: Statistics Utilities
### calculatePDF
File: statistics_test.py
#### Positive tests:
- [] Test that a PDF of a state transition has a sum of approximately 1

#### Negative tests:

### calculateSojourn
File: statistics_test.py
#### Positive tests:

#### Negative tests: