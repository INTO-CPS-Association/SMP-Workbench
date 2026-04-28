
function RadioButtonGroup() {
    return (
        <div >
            <div>
                <label >
                    <input type="radio" name="RadioSelectMode" value="option1" />
                    Analyze files
                </label>
            </div>
            <div>
                <label >
                    <input type="radio" name="RadioSelectMode" value="option2" />
                    Load project    
                </label>
            </div>
        </div>
        );
}

export default RadioButtonGroup;
