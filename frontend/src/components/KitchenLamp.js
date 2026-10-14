import React, {useState, useEffect, useContext, useRef} from 'react';
import {LiveDeviceContext} from "../LiveDeviceContext";
import {useExpandable} from "../ExpandableContext";

const KitchenLamp = (props) => {
    const empty = {"brightness": [], "name": "klamp"};
    const [entry, setEntry] = useState(empty);
    const deviceContext = useContext(LiveDeviceContext);
    const { isExpanded, toggle } = useExpandable();
    const debounceRef = useRef();


    const isLive = () => {
        if (deviceContext && typeof deviceContext.find !== "undefined") {
            const dev = deviceContext.find(obj => {
                return obj.name === 'klamp'
            })
            return dev && dev.value
        }
        return false
    }

    useEffect(() => {
        const socket = new WebSocket(process.env.REACT_APP_HOMECTRL_RESTAPI_URL + '/ws/state');
        socket.onopen = () => {
            console.log('WebSocket connection established.');
        };
        socket.onmessage = (event) => {
            //console.log(event.data)
            const receivedMessage = JSON.parse(event.data);
            const klamp = receivedMessage.result.find(obj => obj.name === 'klamp');
            setEntry(klamp);
        };
        // Initial fetch
        setEntry(empty);
        return () => {
            socket.close();
        };
    }, []);


    function handleRangeChange(e, index) {
        entry.brightness[index] = e.target.value;
        if (debounceRef.current) clearTimeout(debounceRef.current);
        debounceRef.current = setTimeout(() => {
            fetch(process.env.REACT_APP_HOMECTRL_RESTAPI_URL + '/control', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: 'klamp', brightness: entry.brightness }),
            });
        }, 300);
    }


    return (
        <div className="card border-light mb-3" style={{maxWidth: '30rem'}}>
            <div
                className="card-header"
                style={{cursor: 'pointer'}}
                onClick={() => toggle(props.facet)}>
                Kitchen Lamp
            </div>
            {isExpanded(props.facet) && (
            <div className="card-body">
                <ul className="list-group">

                    <li className={"list-group-item" + (isLive() ? "" : " text-decoration-line-through")}>

                        {entry['brightness'].map((value, index) => {
                            return (
                                <div className="d-flex flex-row align-items-center mb-3">
                                    <div>
                                        <button type="button" className="btn btn-outline-warning disabled"
                                                style={{width: '100px'}}>#{index}</button>
                                    </div>
                                    <div className="text-center ms-2">
                                        <span className="badge bg-secondary">{value}%</span>
                                    </div>
                                    <div className="d-flex flex-grow-1 justify-content-center ms-2">
                                        <input type="range" className="form-range"
                                               min="0" max="100" step="1"
                                               id={"ctrl_brightness_" + index}
                                               value={value}
                                               onChange={(e) => handleRangeChange(e, index)}
                                        />
                                    </div>
                                </div>
                            );
                        })}

                    </li>

                </ul>
            </div>
            )}
        </div>
    );


};

export default KitchenLamp;


