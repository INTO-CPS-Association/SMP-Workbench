import React from 'react';
import './App.css';
import Home from './pages/home'
import Loading from './pages/loading'
import Flow from './pages/Flow'
import { BrowserRouter, Route, Routes } from 'react-router-dom';

const App = () => {

  return (
    <BrowserRouter>
      <Routes>
      <Route path="/" element={<Home/>} />
      <Route path="/loading" element={<Loading />} />
      <Route path="/flow" element={<Flow />} />
      </Routes>
    </BrowserRouter>
  );
};

export default App;