import React, { useState, useEffect } from 'react';

const DeviceList = () => {
    const [devices, setDevices] = useState([]);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const response = await fetch(process.env.REACT_APP_HOMECTRL_RESTAPI_URL + '/live');
                const data = await response.json();
                setDevices(data.result);
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
            <h2>Device Status</h2>
            <ul>
                {devices.map((device, index) => (
                    <li key={index}>
                        <strong>{device.name}</strong>: <span className={"live_" + (device.is_alive ? 'on' : 'off')}> {device.is_alive ? 'ON' : 'OFF'} </span> <small>since: {new Date(device.timestamp).toLocaleString()}</small>
                    </li>
                ))}
            </ul>
        </div>
    );
};

export default DeviceList;

