function RadioButton() {
  const [selectedOption, setSelectedOption] = React.useState('');

  const handleOptionChange = (event) => {
    setSelectedOption(event.target.value);
  };

  return <label>
        <input
          type="radio"
          value="option1"
          checked={selectedOption === 'option1'}
          onChange={handleOptionChange}
        />
        Option 1
      </label>
}

export default RadioButton;