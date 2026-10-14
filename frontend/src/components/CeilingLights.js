import React, {useState, useEffect, useContext} from 'react';
import {useExpandable} from "../ExpandableContext";


const CeilingLights = (props) => {
    const [entries, setEntries] = useState([]);
    const { isExpanded, toggle } = useExpandable();
    const excludeNames = ['A0', 'A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'A7', 'B0', 'B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7'];


    const handleClick = (name) => {
        // props.setChartData({model: props.facet, name:name, label:props.label});
        // setTimeout(() => {
        //     if (props.chartRef.current) {
        //         props.chartRef.current.scrollIntoView({ behavior: 'smooth' });
        //     }
        // }, 0);
    };

    useEffect(() => {
        const socket = new WebSocket(process.env.REACT_APP_HOMECTRL_RESTAPI_URL + '/ws/light');
        socket.onopen = () => {
            console.log('WebSocket connection established.');
        };
        socket.onmessage = (event) => {
            //console.log(event.data)
            const receivedMessage = JSON.parse(event.data);
            const aList = [];
            for (const l of receivedMessage.result) {
                if (excludeNames.indexOf(l.name) < 0) {
                    aList.push(l);
                }
            }
            setEntries(aList);
            console.log(receivedMessage);
            console.log(aList);


        };
        // Initial fetch
        setEntries([]);
        return () => {
            socket.close();
        };
    }, [props.facet]);


    return (
        <div className="card border-light mb-3" style={{maxWidth: '30rem'}}>
            <div
                className="card-header"
                style={{cursor: 'pointer'}}
                onClick={() => toggle(props.facet)}>
                {props.label}
            </div>
            {isExpanded(props.facet) && (
            <div className="card-body">
                <span className="card-text">
                    <ul className="list-group">
                        {entries.map((device, index) => (
                            <li
                                key={index}
                                className={"list-group-item d-flex justify-content-between align-items-center"}
                                onClick={() => handleClick(device.name)}>
                                <strong>{device.name}</strong>
                                <small className="text-body-tertiary text-center">{new Date(device.create_at).toLocaleDateString()}<br/>{new Date(device.create_at).toLocaleTimeString()}</small>
                                <span
                                    className={"badge " + (device.value ? 'bg-warning' : 'bg-secondary')}> {device.value ? 'ON' : 'OFF'} </span>
                            </li>
                        ))}
                    </ul>
                </span>
            </div>
            )}
        </div>
    );
};

export default CeilingLights;

