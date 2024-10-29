import React, {useContext} from 'react';
import {LiveDeviceContext} from "../LiveDeviceContext";

const DeviceList = () => {

    const devices = useContext(LiveDeviceContext);

    return (

        <div className="card border-light mb-3" style={{ maxWidth: '30rem' }}>
            <div className="card-header">Device Status</div>
            <div className="card-body">
                <span className="card-text">
                    <ul className="list-group">
                        {devices && typeof devices.map !== "undefined" && devices.map((device, index) => (
                            <li key={index} className="list-group-item d-flex justify-content-between align-items-center">
                                <strong>{device.name}</strong>
                                <small
                                    className="text-body-tertiary text-center">{new Date(device.create_at).toLocaleDateString()}<br/>{new Date(device.create_at).toLocaleTimeString()}
                                </small>
                                <span
                                    className={"badge rounded-pill " + (device.value ? 'bg-success' : 'bg-danger')}> {device.value ? 'ON' : 'OFF'} </span>
                            </li>
                        ))}
                    </ul>
                </span>
            </div>
        </div>
    );
};

export default DeviceList;

