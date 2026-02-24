# Test List
This is the complete list of tests in the project. The tests will be categorized into different sections with respect to the subsystem that they test. There are both positive and negative tests.

## Subsystem: File Management
### JsonFileReadingStrategy
File: json_file_reading_strategy_test.py
#### Positive tests:
- [OK] Test that the read method in JsonFileReadingStrategy returns a json object when given a .json file.
- [OK] Test that the read method in JsonFileReadingStrategy returns an instance of a JsonFileWrapper class.
#### Negative tests:
- [OK] Test that the read method in JsonFileReadingStrategy raises an OSError exception when the given path to the file does not end with '.json'
    - [OK] Test that the OSError exception contains a value="File did not end with .json".

## SubSystem: Log Parsing
### JsonLogParsingStrategy
File: json_log_parsing_strategy_test.py
#### Positive tests:
- [OK] Test that the getStates method in the JsonLogParsingStrategy has a return value of type set.
- [OK] Test that the getStates method in the JsonLogParsingStrategy returns the complete set of states.
- [OK] Test that the computePDF method in JsonLogParsingStrategy returns a list of StandardStateTransition objects that has the same amount of elements as the number of unique states.
- [OK] Test that the count of a transition is at least 1
- [OK] Test that the sum of toStates in StandardStateTransition is approximately 1 (PDF). This checks that the computePDF method in JsonLogParsingStrategy works properly.
- [ ] Test that the computeSojournTimes method in JsonLogParsingStrategy can retreive Sojourn times for the different transitions
#### Negative tests:
- NIL
