import React, { useState, useEffect } from 'react';

const EntryBoolean = (props) => {
    const [entries, setEntries] = useState([]);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const response = await fetch(process.env.REACT_APP_HOMECTRL_RESTAPI_URL + '/' + props.model);
                const data = await response.json();
                setEntries(data.result);
            } catch (error) {
                console.error('Error fetching data:', error);
            }
        };

        fetchData();

        // Fetch every 10 seconds
        const intervalId = setInterval(fetchData, 5 * 1000);

        // Cleanup interval on component unmount
        return () => clearInterval(intervalId);
    }, []);

    const handleClick = (name) => {
        props.setChartData({model: props.model, name:name, label:props.label});
        setTimeout(() => {
            if (props.chartRef.current) {
                props.chartRef.current.scrollIntoView({ behavior: 'smooth' });
            }
        }, 0);
    };

    return (
        <div className="card border-light mb-3" style={{maxWidth: '30rem'}}>
            <div className="card-header">{props.label}</div>
            <div className="card-body">
                <span className="card-text">
                    <ul className="list-group">
                        {entries.map((device, index) => (
                            <li
                                key={index}
                                className="list-group-item d-flex justify-content-between align-items-center"
                                onClick={() => handleClick(device.name)}>
                                <strong>{device.name}</strong>
                                <small className="text-body-tertiary text-center">{new Date(device.timestamp).toLocaleDateString()}<br/>{new Date(device.timestamp).toLocaleTimeString()}</small>
                                <span
                                    className={"badge " + (device.value ? 'bg-warning' : 'bg-secondary')}> {device.value ? 'ON' : 'OFF'} </span>
                            </li>
                        ))}
                    </ul>
                </span>
            </div>
        </div>
    );
};

export default EntryBoolean;

