import React, { useState, useEffect } from 'react';

const Laundry = () => {
    const [laundry, setLaundry] = useState({});

    useEffect(() => {
        const socket = new WebSocket(process.env.REACT_APP_HOMECTRL_RESTAPI_URL + '/ws/activity');
        socket.onopen = () => {
            console.log('WebSocket connection established.');
        };
        socket.onmessage = (event) => {
            //console.log(event.data)
            const receivedMessage = JSON.parse(event.data);
            for (const activity of receivedMessage.result){
                if (activity.name === "laundry") {
                    setLaundry(activity);
                    break;
                }
            }
        };
        setLaundry({});
        return () => {
            socket.close();
        };
    }, []);

    return (
        <div className="card border-light mb-3" style={{maxWidth: '30rem'}}>
            <div className="card-header">Laundry</div>
            <div className="card-body">
                <ul className="list-group">
                    <li className="list-group-item">

                        <div className="d-flex justify-content-end align-items-center">
                            <span
                                className={"badge " + (laundry.is_active ? 'bg-warning' : 'bg-secondary')}> {laundry.is_active ? 'ON' : 'OFF'} </span>
                        </div>

                        <table className="table table-dark align-middle table-sm">
                            <tbody>
                            <tr>
                                <th colSpan="4">
                                    <strong>{laundry.is_active ? 'Current' : 'Last'} laundry:</strong>
                                </th>
                            </tr>
                            <tr>
                            <th className="text-end">Start</th>
                                <td>
                                    <small
                                        className="text-body-tertiary text-center">{new Date(laundry.start_at).toLocaleDateString()}<br/>{new Date(laundry.start_at).toLocaleTimeString()}
                                    </small>
                                </td>
                                <th className="text-end">End</th>
                                <td>
                                    {!laundry.is_active &&
                                        <small
                                            className="text-body-tertiary text-center">{new Date(laundry.end_at).toLocaleDateString()}<br/>{new Date(laundry.end_at).toLocaleTimeString()}
                                        </small>
                                    }
                                </td>
                            </tr>
                            {!laundry.is_active &&
                                <tr>
                                    <th className="text-end" colSpan="2">Energy consumed</th>
                                    <td colSpan="2">
                                        <span className="text-success">{laundry.energy}</span>
                                        <span className="text-info">kWh</span>
                                    </td>
                                </tr>
                            }
                            {!laundry.is_active &&
                                <tr>
                                    <th className="text-end" colSpan="1">Duration</th>
                                    <td colSpan="3">
                                    <span className="text-success">{laundry.duration}</span>
                                </td>
                            </tr>
                            }
                            </tbody>
                        </table>
                    </li>
                </ul>
            </div>
        </div>
    );
}

export default Laundry;

