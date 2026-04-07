import React from 'react';
import './App.css';
import Home from './pages/home'
import Loading from './pages/loading'
import { BrowserRouter, Route, Routes } from 'react-router-dom';

const App = () => {

  return (
    <BrowserRouter>
      <Routes>
      <Route path="/" element={<Home/>} />
      <Route path="/loading" element={<Loading />} />
      </Routes>
    </BrowserRouter>
  );
};

export default App;