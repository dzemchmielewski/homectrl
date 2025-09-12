import React, {useContext} from 'react';
import {LiveDeviceContext} from "../LiveDeviceContext";
import {useExpandable} from "../ExpandableContext";

const DeviceList = (props) => {

    const devices = useContext(LiveDeviceContext);
    const { isExpanded, toggle } = useExpandable();

    return (

        <div className="card border-light mb-3" style={{ maxWidth: '30rem' }}>
            <div
                className="card-header"
                style={{cursor: 'pointer'}}
                onClick={() => toggle(props.facet)}>
                Device Status
            </div>
            {isExpanded(props.facet) && (
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
            )}
        </div>
    );
};

export default DeviceList;

