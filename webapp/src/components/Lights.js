import React, { useState, useEffect } from 'react';

const Lights = () => {
    const [lights, setLights] = useState([]);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const response = await fetch(process.env.REACT_APP_HOMECTRL_RESTAPI_URL + '/lights');
                const data = await response.json();
                setLights(data.result);
            } catch (error) {
                console.error('Error fetching data:', error);
            }
        };

        // Initial fetch
        fetchData();

        // Fetch every 10 seconds
        const intervalId = setInterval(fetchData, 5 * 1000);

        // Cleanup interval on component unmount
        return () => clearInterval(intervalId);
    }, []);

    return (
        <div className="list">
        <h2>Lights</h2>
            <ul>
                {lights.map((device, index) => (
                    <li key={index}>
                        <strong>{device.name}</strong>: <span
                        className={"lights_" + (device.value ? 'on' : 'off')}> {device.value ? 'ON' : 'OFF'} </span>
                        <small>since: {new Date(device.timestamp).toLocaleString()}</small>
                    </li>
                ))}
            </ul>
        </div>
    );
};

export default Lights;

