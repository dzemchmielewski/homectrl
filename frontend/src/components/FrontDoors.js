import React, {useState, useEffect, useContext} from 'react';
import {LiveDeviceContext, IsAlive} from "../LiveDeviceContext";
import {useExpandable} from "../ExpandableContext";


const FrontDoors = (props) => {
    const [entriesDoors, setEntriesDoors] = useState([]);
    const [entriesBell, setEntriesBell] = useState([]);
    const deviceContext = useContext(LiveDeviceContext);
    const { isExpanded, toggle } = useExpandable();

    const handleClick = (name) => {
        props.setChartData({model: props.facet, name:name, label:props.label});
        setTimeout(() => {
            if (props.chartRef.current) {
                props.chartRef.current.scrollIntoView({ behavior: 'smooth' });
            }
        }, 0);
    };

    useEffect(() => {
        const socketDoors = new WebSocket(process.env.REACT_APP_HOMECTRL_RESTAPI_URL + '/ws/doors');
        const socketBell = new WebSocket(process.env.REACT_APP_HOMECTRL_RESTAPI_URL + '/ws/bell');
        socketDoors.onmessage = (event) => {
            setEntriesDoors(JSON.parse(event.data).result);
        };
        socketBell.onmessage = (event) => {
            setEntriesBell(JSON.parse(event.data).result);
        };
        // Initial fetch
        setEntriesDoors([]);
        setEntriesBell([]);
        return () => {
            socketDoors.close();
            socketBell.close();
        };
    }, []);


    return (
        <div className="card border-light mb-3" style={{maxWidth: '30rem'}}>
            <div
                className="card-header"
                style={{cursor: 'pointer'}}
                onClick={() => toggle(props.facet)}>
                Front Doors
            </div>
            {isExpanded(props.facet) && (
                <div className="card-body">
                <span className="card-text">
                    <ul className="list-group">
                        {entriesDoors.map((device, index) => (
                            <li
                                key={index}
                                className={"list-group-item d-flex justify-content-between align-items-center" + (IsAlive(device.name, deviceContext) ? "" : " text-decoration-line-through")}
                                onClick={() => handleClick(device.name)}>
                                <strong>doors</strong>
                                <small className="text-body-tertiary text-center">{new Date(device.create_at).toLocaleDateString()}<br/>{new Date(device.create_at).toLocaleTimeString()}</small>
                                <span
                                    className={"badge " + (device.value ? 'bg-warning' : 'bg-secondary')}> {device.value ? 'ON' : 'OFF'} </span>
                            </li>
                        ))}
                        {entriesBell.map((device, index) => (
                            <li
                                key={index}
                                className={"list-group-item d-flex justify-content-between align-items-center" + (IsAlive(device.name, deviceContext) ? "" : " text-decoration-line-through")}
                                onClick={() => handleClick(device.name)}>
                                <strong>bell</strong>
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

export default FrontDoors;
