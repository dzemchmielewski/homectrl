import React, {useState, useEffect} from 'react';

const Electricity = () => {
    const [entries, setEntries] = useState([]);

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
            <div className="card-header">Electricity</div>
            <div className="card-body">
                <ul className="list-group">
                    {entries.map((entry, index) => (
                        <li key={index} className="list-group-item">
                            <div className="d-flex justify-content-start align-items-center mb-3">
                                <strong>{entry.name}</strong>
                            </div>
                            <table className="table table-dark">
                                <tbody>
                                <tr>
                                    <th className="text-end">V</th>
                                    <td>
                                        <span className="text-success">{entry.voltage}</span>
                                        <span className="text-info">V</span>
                                    </td>
                                    <th className="text-end">AP</th>
                                    <td>
                                        <span className="text-success">{entry.active_power}</span>
                                        <span className="text-info">W</span>
                                    </td>
                                    <th className="text-end">I</th>
                                    <td>
                                        <span className="text-success">{entry.current}</span>
                                        <span className="text-info">A</span>
                                    </td>
                                </tr>
                                <tr>
                                    <th className="text-end">AE</th>
                                    <td>
                                        <span className="text-success">{entry.active_energy / 1000}</span>
                                        <span className="text-info">kWh</span>
                                    </td>
                                    <th className="text-end">PF</th>
                                    <td>
                                        <span className="text-success">{entry.power_factor * 100}</span>
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
        </div>
    );


};

export default Electricity;


