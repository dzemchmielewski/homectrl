import React, {useState, useEffect, useContext} from 'react';
import {IsAlive, LiveDeviceContext} from "../LiveDeviceContext";
import {useExpandable} from "../ExpandableContext";

const Controls = (props) => {
    const [state, setState] = useState([]);
    const [capabilities, setCapabilities] = useState({})
    const deviceContext = useContext(LiveDeviceContext)
    const { isExpanded, toggle } = useExpandable();

    const sendControl = (event, device, control, value) => {
        // console.log("Device: " + device + ", control: " + control + ", value: "+ value)
        // console.log("sendControl event:: " + event.target.value)

        const newState = state.map((item) => {
            if (item.name === device) {
                const updatedItem = {...item};
                updatedItem[control] = value
                return updatedItem;
            }
            return item;
        });
        setState(newState)

        fetch(process.env.REACT_APP_HOMECTRL_RESTAPI_URL + '/control',
            {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: '{ "name": "' + device + '", "'  + control + '": "' + value + '"}'
        });


    }

    useEffect(() => {

        const socket = new WebSocket(process.env.REACT_APP_HOMECTRL_RESTAPI_URL + '/ws/state');
        socket.onopen = () => {
            console.log('WebSocket connection established.');
        };
        socket.onmessage = (event) => {
            //console.log(event.data)
            const receivedMessage = JSON.parse(event.data);
            setState(receivedMessage.result);
        };

        const fetchCapabilities = async () => {
            try {
                const response = await fetch(process.env.REACT_APP_HOMECTRL_RESTAPI_URL + '/capabilities');
                const data = await response.json();
                setCapabilities(data);
            } catch (error) {
                console.error('Error fetching data:', error);
            }
        };
        fetchCapabilities()
        setState([]);

        return () => {
            socket.close();
        };
    }, []);

    function show_controls(name, controls) {
        let deviceState = state.find(s => s.name === name)
        if (!deviceState) { deviceState = {}}

        return <ul key={"ctrl_" + name} className={"list-group"}>
            {controls.map((c, ctrl_index) => {
                if (["str"].includes(c.type)){
                    if (c.constraints.type === "enum") {
                        const current_value = deviceState[c.name]
                        return <li key={ctrl_index} className={"list-group-item ps-0"}>
                            <div className="d-flex flex-row align-items-center">
                                <span className={"m-3"}>{c.name}</span>
                                <div className="btn-group" role="group">
                                    {c.constraints.values.map((value, val_index) => {
                                        return <>
                                            <input type="radio" className="btn-check"
                                                   // autoComplete="off"
                                                   name={"ctrl_" + name + "_control_" + ctrl_index}
                                                   id={"ctrl_" + name + "_control_" + ctrl_index + "_option_" + val_index}
                                                   checked={current_value === value}
                                                   onChange={(e) => sendControl(e, name, c.name, value)}
                                            />
                                            <label className="btn btn-outline-primary" htmlFor={"ctrl_" + name + "_control_" + ctrl_index + "_option_" + val_index}>{value}</label>
                                        </>
                                    })}
                                </div>
                            </div>

                        </li>
                    }
                }
                // return <li key={ctrl_index}>
                //     <span>{c.name}</span> <small>not available</small>
                // </li>
            })}
        </ul>
    }

    function renderDeviceControls() {
        return Object.keys(capabilities).map(name => {
            if (!IsAlive(name, deviceContext)) {
                return null;
            }
            return (
                <li key={name}
                    className="list-group-item d-flex justify-content-around align-items-center ps-1">
                    <div>{name}</div>
                    {show_controls(name, capabilities[name].controls)}
                </li>
            );
        }).filter(Boolean);
    }

    return (
        <div className="card border-light mb-3" style={{maxWidth: '30rem'}}>
            <div
                className="card-header"
                style={{cursor: 'pointer'}}
                onClick={() => toggle(props.facet)}>
                Controls
            </div>
            {isExpanded(props.facet) && (
            <div className="card-body">
                <span className="card-text">
                    <ul className="list-group">
                        {renderDeviceControls()}
                    </ul>
                </span>
            </div>
            )}
        </div>
    );
};

export default Controls;

