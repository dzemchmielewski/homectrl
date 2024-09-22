import React, {useRef, useState} from 'react';
import './App.css';
import DeviceList from './components/DeviceList';
import Radio from "./components/Radio";
import EntryBoolean from "./components/EntryBoolean";
import EntryDecimal from "./components/EntryDecimal";
import Chart from "./components/Chart";

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

            <div className="container">
                <div class="row">
                    <div className="col">
                        <DeviceList />
                        <EntryBoolean model="presence" label="Presence" setChartData={setChartData} chartRef={chartRef}/>
                        <EntryBoolean model="light" label="Lights" setChartData={setChartData} chartRef={chartRef}/>
                    </div>
                    <div className="col">
                        <EntryBoolean model="darkness" label="Darkness" setChartData={setChartData} chartRef={chartRef}/>
                        <EntryDecimal model="temperature" label="Temperature" unit="°C" setChartData={setChartData} chartRef={chartRef}/>
                        <EntryDecimal model="humidity" label="Humidity" unit="%" setChartData={setChartData} chartRef={chartRef}/>
                        <EntryDecimal model="pressure" label="Pressure" unit={"hPa"} setChartData={setChartData} chartRef={chartRef}/>
                    </div>
                    <div className="col" class="w-100 p-3">
                        <Radio/>
                        <Chart chartData={chartData} ref={chartRef}/>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default App;