import React from 'react';
import './App.css';
import FruitList from './components/Fruits';

const App = () => {
  return (
    <div className="App">
      <header className="App- header">
        <h1>SMP-Visualizer</h1>
      </header>
      
      <main>
        <h3>Select files to analyze</h3>  
        <label>
            <input type="file" id="file-picker" name="fileList" webkitdirectory multiple />
        </label>
      </main>
    </div>
  );
};

export default App;