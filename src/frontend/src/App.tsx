import React from 'react';
import './App.css';
import Button from "./components/Button";
import RadioButtonGroup from "./components/RadioButtonGroup";

const App = () => {
  return (
    <div className="App">
      <header className="App- header">
        <h1>SMP-Visualizer</h1>
      </header>
      <main>
        <h3 className="Header3">Select files to analyze</h3>  
        <label>
            <input type="file" className="FileExplorer" accept=".json" id="file-picker" multiple/>
        </label>
        <h3>Load an existing project</h3>
        <label>
            <input type="file" className="FileExplorer" accept=".json" id="file-picker"/>
        </label>
        <h3>
          Select mode
        </h3>
        <RadioButtonGroup />  
        <div>
          <Button />
        </div>
      </main>
    </div>
  );
};

export default App;