import React, { useState, useEffect } from 'react';

const DeviceList = () => {
    const [devices, setDevices] = useState([]);

    useEffect(() => {
        const socket = new WebSocket(process.env.REACT_APP_HOMECTRL_RESTAPI_URL + '/ws/live');
        socket.onopen = () => {
            console.log('WebSocket connection established.');
        };
        socket.onmessage = (event) => {
            //console.log(event.data)
            const receivedMessage = JSON.parse(event.data);
            setDevices(receivedMessage.result);
        };
        // Initial fetch
        setDevices([]);
        return () => {
            socket.close();
        };
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
                                    className="text-body-tertiary text-center">{new Date(device.create_at).toLocaleDateString()}<br/>{new Date(device.create_at).toLocaleTimeString()}
                                </small>
                                <span
                                    className={"badge rounded-pill " + (device.value ? 'bg-success' : 'bg-danger')}> {device.value ? 'ON' : 'OFF'} </span>
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

