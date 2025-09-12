import React, { useState, useEffect } from 'react';
import {useExpandable} from "../ExpandableContext";

const Radio = (props) => {
    const [radio, setRadio] = useState({});
    const { isExpanded, toggle } = useExpandable();

    useEffect(() => {
        const socket = new WebSocket(process.env.REACT_APP_HOMECTRL_RESTAPI_URL + '/ws/radio');
        socket.onopen = () => {
            console.log('WebSocket connection established.');
        };
        socket.onmessage = (event) => {
            //console.log(event.data)
            const receivedMessage = JSON.parse(event.data);
            setRadio(receivedMessage.result[0]);
        };
        // Initial fetch
        setRadio({});
        return () => {
            socket.close();
        };
    }, []);

    if (radio.live) {
        return (
            <div className="card border-light mb-3" style={{maxWidth: '30rem'}}>
                <div
                    className="card-header"
                    style={{cursor: 'pointer'}}
                    onClick={() => toggle(props.facet)}>
                    Radio
                </div>
                {isExpanded(props.facet) && (
                <div className="card-body">
                    <h5 className="card-title">{radio.station_name}</h5>
                    {radio.playinfo &&
                        <h6 className="card-subtitle text-muted">{radio.playinfo}</h6>
                    }
                </div>
                )}
            </div>
        );
    }
    return null;
};

export default Radio;

