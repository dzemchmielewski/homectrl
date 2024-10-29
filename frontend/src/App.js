import React, {useRef, useState} from 'react';
import './App.css';
import {LiveDeviceProvider} from "./LiveDeviceContext";
import DeviceList from './components/DeviceList';
import Radio from "./components/Radio";
import EntryBoolean from "./components/EntryBoolean";
import EntryDecimal from "./components/EntryDecimal";
import Chart from "./components/Chart";
import Electricity from "./components/Electricity";
import Laundry from "./components/Laundry";
import Controls from "./components/Controls";

function App() {

    const [chartData, setChartData] = useState({
            model: undefined,
            name: undefined,
            label: undefined,
        });
    const chartRef = useRef(null);

    return (
        <div className="App">

            <ol className="breadcrumb">
                <li className="breadcrumb-item active"><h3>DZEM HomeCtrl</h3></li>
            </ol>

            <LiveDeviceProvider>
                <div className="container">
                    <div className="row">
                        <div className="col">
                            <DeviceList/>
                            <EntryBoolean facet="presence" label="Presence" setChartData={setChartData} chartRef={chartRef}/>
                            <EntryBoolean facet="light" label="Lights" setChartData={setChartData} chartRef={chartRef}/>
                        </div>
                        <div className="col">
                            <EntryBoolean facet="darkness" label="Darkness" setChartData={setChartData} chartRef={chartRef}/>
                            <EntryDecimal facet="temperature" label="Temperature" unit="°C" setChartData={setChartData} chartRef={chartRef}/>
                            <EntryDecimal facet="humidity" label="Humidity" unit="%" setChartData={setChartData} chartRef={chartRef}/>
                            <EntryDecimal facet="pressure" label="Pressure" unit={"hPa"} setChartData={setChartData} chartRef={chartRef}/>
                        </div>
                        <div className="col">
                            <Electricity/>
                            <Laundry/>
                            <Radio/>
                            <Controls/>
                            <Chart chartData={chartData} ref={chartRef}/>
                        </div>
                    </div>
                </div>
            </LiveDeviceProvider>

        </div>
    );
}

export default App;