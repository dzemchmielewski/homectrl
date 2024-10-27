import React, {createContext, useState, useEffect} from 'react';

export const LiveDeviceContext = createContext({});

export const LiveDeviceProvider = ({children}) => {
    const [devices, setDevices] = useState({});

    useEffect(() => {
        const socket = new WebSocket(process.env.REACT_APP_HOMECTRL_RESTAPI_URL + '/ws/live');

        socket.onmessage = (event) => {
            const receivedMessage = JSON.parse(event.data);
            setDevices(receivedMessage.result);
        };

        return () => socket.close();
    }, []);

    return (
        <LiveDeviceContext.Provider value={devices}>
            {children}
        </LiveDeviceContext.Provider>
    );
};