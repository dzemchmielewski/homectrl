import React, { useState, useEffect } from 'react';

const Radio = () => {
    const [radio, setRadio] = useState({});

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
                <div className="card-header">Radio</div>
                <div className="card-body">
                    <h5 className="card-title">{radio.station_name}</h5>
                    {radio.playinfo &&
                        <h6 className="card-subtitle text-muted">{radio.playinfo}</h6>
                    }
                </div>
            </div>
        );
    }
    return null;
};

export default Radio;

