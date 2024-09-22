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

        <div className="card border-light mb-3" style={{ maxWidth: '30rem' }}>
            <div className="card-header">Device Status</div>
            <div className="card-body">
                <span className="card-text">
                    <ul className="list-group">
                        {devices.map((device, index) => (
                            <li key={index} className="list-group-item d-flex justify-content-between align-items-center">
                                <strong>{device.name}</strong>
                                <small
                                    className="text-body-tertiary text-center">{new Date(device.timestamp).toLocaleDateString()}<br/>{new Date(device.timestamp).toLocaleTimeString()}
                                </small>
                                <span
                                    className={"badge rounded-pill " + (device.is_alive ? 'bg-success' : 'bg-danger')}> {device.is_alive ? 'ON' : 'OFF'} </span>
                            </li>
                        ))}
                        {/*<li>*/}
                        {/*    <button type="button" className="btn btn-secondary" data-bs-container="body" data-bs-toggle="popover" data-bs-placement="top" data-bs-content="Vivamus sagittis lacus vel augue laoreet rutrum faucibus." data-bs-original-title="Popover Title" aria-describedby="popover200733">Top</button>*/}
                        {/*</li>*/}
                    </ul>
                </span>
            </div>
        </div>
    );
};

export default DeviceList;

