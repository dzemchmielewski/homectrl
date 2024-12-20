import React, {useState, useEffect, useContext} from 'react';
import {LiveDeviceContext, IsAlive} from "../LiveDeviceContext";

const EntryDecimal = (props) => {
    const [entries, setEntries] = useState([]);
    const deviceContext = useContext(LiveDeviceContext)

    const handleClick = (name) => {
        props.setChartData({model: props.facet, name:name, label:props.label});
        setTimeout(() => {
            if (props.chartRef.current) {
                props.chartRef.current.scrollIntoView({ behavior: 'smooth' });
            }
        }, 0);
    };

    useEffect(() => {
        const socket = new WebSocket(process.env.REACT_APP_HOMECTRL_RESTAPI_URL + '/ws/' + props.facet);
        socket.onopen = () => {
            console.log('WebSocket connection established.');
        };
        socket.onmessage = (event) => {
            //console.log(event.data)
            const receivedMessage = JSON.parse(event.data);
            setEntries(receivedMessage.result);
        };
        // Initial fetch
        setEntries([]);
        return () => {
            socket.close();
        };
    }, [props.facet]);

    return (
        <div className="card border-light mb-3" style={{maxWidth: '30rem'}}>
            <div className="card-header">{props.label}</div>
            <div className="card-body">
                <span className="card-text">
                    <ul className="list-group">
                        {entries.map((device, index) => (
                            <li
                                key={index}
                                className={"list-group-item d-flex justify-content-between align-items-center" + (IsAlive(device.name, deviceContext) ? "" : " text-decoration-line-through")}
                                onClick={() => handleClick(device.name)}>
                                <strong>{device.name}</strong>
                                <small
                                    className="text-body-tertiary text-center">{new Date(device.create_at).toLocaleDateString()}<br/>{new Date(device.create_at).toLocaleTimeString()}
                                </small>
                                <div>
                                    <span className="text-success"> {device.value} </span>
                                    <span className="text-info">{props.unit}</span>
                                </div>
                            </li>
                        ))}
                    </ul>
                </span>
            </div>
        </div>
    );
};

export default EntryDecimal;

