import React from 'react';
import './App.css';
import Home from './pages/Home'
import Loading from './pages/Loading'
import Flow from './pages/Flow'
import Statistics from './pages/Statistics'
import { BrowserRouter, Route, Routes } from 'react-router-dom';

const App = () => {

  return (
    <BrowserRouter>
      <Routes>
      <Route path="/" element={<Home/>} />
      <Route path="/loading" element={<Loading />} />
      <Route path="/flow" element={<Flow />} />
      <Route path="/statistics" element={<Statistics />} />
      </Routes>
    </BrowserRouter>
  );
};

export default App;