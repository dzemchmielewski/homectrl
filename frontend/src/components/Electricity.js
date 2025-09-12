import React, {useState, useEffect, useContext} from 'react';
import {LiveDeviceContext} from "../LiveDeviceContext";
import {useExpandable} from "../ExpandableContext";

const Electricity = (props) => {
    const [entries, setEntries] = useState([]);
    const deviceContext = useContext(LiveDeviceContext);
    const { isExpanded, toggle } = useExpandable();

    const isLive = (name) => {
        if (deviceContext && typeof deviceContext.find !== "undefined") {
            const dev = deviceContext.find(obj => {
                return obj.name === name
            })
            return dev && dev.value
        }
        return false
    }

    useEffect(() => {
        const socket = new WebSocket(process.env.REACT_APP_HOMECTRL_RESTAPI_URL + '/ws/electricity');
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
    }, []);

    return (
        <div className="card border-light mb-3" style={{maxWidth: '30rem'}}>
            <div
                className="card-header"
                style={{cursor: 'pointer'}}
                onClick={() => toggle(props.facet)}>
                Electricity
            </div>
            {isExpanded(props.facet) && (
            <div className="card-body">
                <ul className="list-group">
                    {entries.map((entry, index) => (
                        <li key={index} className={"list-group-item" + (isLive(entry.name) ? "" : " text-decoration-line-through")}>
                            <div className="d-flex justify-content-start align-items-center mb-3">
                                <strong>{entry.name}</strong>
                            </div>
                            <table className="table table-dark table-sm">
                                <tbody>
                                <tr>
                                    <th className="text-end">V</th>
                                    <td>
                                        <span className="text-success">{entry.voltage.toFixed(1)}</span>
                                        <span className="text-info">V</span>
                                    </td>
                                    <th className="text-end">AP</th>
                                    <td>
                                        <span className="text-success">{entry.active_power.toFixed(1)}</span>
                                        <span className="text-info">W</span>
                                    </td>
                                    <th className="text-end">I</th>
                                    <td>
                                        <span className="text-success">{entry.current.toFixed(3)}</span>
                                        <span className="text-info">A</span>
                                    </td>
                                </tr>
                                <tr>
                                    <th className="text-end">AE</th>
                                    <td>
                                        <span className="text-success">{(entry.active_energy / 1000).toFixed(3)}</span>
                                        <span className="text-info">kWh</span>
                                    </td>
                                    <th className="text-end">PF</th>
                                    <td>
                                        <span className="text-success">{(entry.power_factor * 100).toFixed(0)}</span>
                                        <span className="text-info">%</span>
                                    </td>
                                    <th colSpan="2"></th>
                                </tr>
                                </tbody>
                            </table>
                        </li>
                    ))}
                </ul>
            </div>
            )}
        </div>
    );


};

export default Electricity;


