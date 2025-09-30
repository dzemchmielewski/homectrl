import React, {useState, useEffect, useContext, useRef} from 'react';
import {IsAlive, LiveDeviceContext} from "../LiveDeviceContext";
import {useExpandable} from "../ExpandableContext";

const Controls = (props) => {
    const [state, setState] = useState([]);
    const [capabilities, setCapabilities] = useState({});
    const deviceContext = useContext(LiveDeviceContext);
    const { isExpanded, toggle } = useExpandable();
    const debounceRef = useRef();
    const [sliderValues, setSliderValues] = useState({});

    // Fetch capabilities once on mount
    useEffect(() => {
        const fetchCapabilities = async () => {
            try {
                const response = await fetch(process.env.REACT_APP_HOMECTRL_RESTAPI_URL + '/capabilities');
                const data = await response.json();
                setCapabilities(data);
            } catch (error) {
                console.error('Error fetching data:', error);
            }
        };
        fetchCapabilities();
    }, []);

    // WebSocket and state updates, runs when capabilities change
    useEffect(() => {
        if (!capabilities || Object.keys(capabilities).length === 0) return;

        const socket = new WebSocket(process.env.REACT_APP_HOMECTRL_RESTAPI_URL + '/ws/state');
        socket.onopen = () => {
            console.log('WebSocket connection established.');
        };
        socket.onmessage = (event) => {
            const receivedMessage = JSON.parse(event.data);
            setState(receivedMessage.result);
        };

        // Initialize slider values
        const initialValues = {};
        Object.keys(capabilities).forEach(name => {
            capabilities[name].controls.forEach(c => {
                if (c.constraints.type === "range") {
                    initialValues[name + "_" + c.name] = c.constraints.values.min;
                }
            });
        });
        setSliderValues(initialValues);

        return () => {
            socket.close();
        };
    }, [capabilities]);

    // Update slider values when state changes
    useEffect(() => {
        if (!capabilities || Object.keys(capabilities).length === 0) return;

        const updatedValues = {...sliderValues};
        Object.keys(capabilities).forEach(name => {
            capabilities[name].controls.forEach(c => {
                if (c.constraints.type === "range") {
                    const deviceState = state.find(s => s.name === name) || {};
                    updatedValues[name + "_" + c.name] = deviceState[c.name] ?? c.constraints.values.min;
                }
            });
        });
        setSliderValues(updatedValues);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [state]);

    const sendControl = (event, device, control, value) => {
        const newState = state.map((item) => {
            if (item.name === device) {
                const updatedItem = {...item};
                updatedItem[control] = value;
                return updatedItem;
            }
            return item;
        });
        setState(newState);

        fetch(process.env.REACT_APP_HOMECTRL_RESTAPI_URL + '/control', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: device, [control]: value })
        });
    };

    function handleRangeChange(e, name, controlName) {
        const value = Number(e.target.value);
        setSliderValues(prev => ({
            ...prev,
            [name + "_" + controlName]: value
        }));

        if (debounceRef.current) clearTimeout(debounceRef.current);
        debounceRef.current = setTimeout(() => {
            sendControl(e, name, controlName, value);
        }, 300);
    }

    function show_controls(name, controls) {
        let deviceState = state.find(s => s.name === name);
        if (!deviceState) { deviceState = {}; }

        return (
            <div>
                {controls.map((c, ctrl_index) => {
                    if (["str", "int"].includes(c.type)) {
                        if (c.constraints.type === "enum") {
                            const current_value = deviceState[c.name];
                            return (
                                    <div className="d-flex flex-row align-items-center mb-3">
                                        <div>
                                            <button type="button" className="btn btn-outline-warning disabled" style={{width: '100px'}}>{c.name}</button>
                                        </div>
                                        <div className="d-flex flex-grow-1 justify-content-center ms-2">
                                            <div className="btn-group" role="group">
                                                {c.constraints.values.map((value, val_index) => (
                                                    <React.Fragment key={val_index}>
                                                        <input type="radio" className="btn-check"
                                                               name={"ctrl_" + name + "_control_" + ctrl_index}
                                                               id={"ctrl_" + name + "_control_" + ctrl_index + "_option_" + val_index}
                                                               checked={current_value === value}
                                                               onChange={(e) => sendControl(e, name, c.name, value)}
                                                        />
                                                        <label className="btn btn-outline-primary" htmlFor={"ctrl_" + name + "_control_" + ctrl_index + "_option_" + val_index}>{value}</label>
                                                    </React.Fragment>
                                                ))}
                                            </div>
                                        </div>
                                    </div>
                            );
                        } else if (c.constraints.type === "range") {
                            const current_value = sliderValues[name + "_" + c.name] ?? c.constraints.values.min;
                            return (
                                <div className="d-flex flex-row align-items-center mb-3">
                                    <div>
                                        <button type="button" className="btn btn-outline-warning disabled"
                                                style={{width: '100px'}}>{c.name}</button>
                                    </div>
                                    <div className="text-center ms-2">
                                        <span className="badge bg-secondary">{current_value}%</span>
                                    </div>
                                    <div className="d-flex flex-grow-1 justify-content-center ms-2">
                                        <input type="range" className="form-range"
                                               min={c.constraints.values.min} max={c.constraints.values.max} step="1"
                                               id={"ctrl_" + name + "_control_" + ctrl_index + "_range"}
                                               value={current_value}
                                               onChange={(e) => handleRangeChange(e, name, c.name)}
                                        />
                                    </div>
                                </div>
                            );
                        }
                    }
                    return null;
                })}
            </div>
        );
    }

    function renderDeviceControls() {
        return Object.keys(capabilities).map(name => {
            if (!IsAlive(name, deviceContext) || !capabilities[name].controls || capabilities[name].controls.length === 0) {
                return null;
            }
            return (
                <div className="card border-secondary mb-3" key={name}>
                    <div className="card-header">{name}</div>
                    <div className="card-body">
                        <span className="card-text">
                            {show_controls(name, capabilities[name].controls)}
                        </span>
                    </div>
                </div>
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
                        {renderDeviceControls()}
                    </span>
                </div>
            )}
        </div>
    );
};

export default Controls;
