import React from 'react';
import './App.css';
import DeviceList from './components/DeviceList';
import Lights from "./components/Lights";
import Radio from "./components/Radio";

function App() {
    return (
        <div className="App">
            <h1>DZEM HomeCtrl</h1>
            <DeviceList />
            <Lights />
            <Radio/>
        </div>
    );
}

export default App;