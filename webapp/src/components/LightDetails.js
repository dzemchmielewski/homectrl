import React, { useState, useEffect } from 'react';

const LightDetails = () => {
    const [lightDetails, setLightDetails] = useState([]);


    useEffect(() => {
        const fetchData = async () => {
            try {
                const response = await fetch(process.env.REACT_APP_HOMECTRL_RESTAPI_URL + '/lights');
                const data = await response.json();
                //setLightDetails({name: "name", value: true, timestamp: "2024-08-25T02:16:03.355972"});
                setLightDetails(data.result)
            } catch (error) {
                console.error('Error fetching data:', error);
            }
        };

        // Initial fetch
        fetchData();

        // Fetch every 10 seconds
        const intervalId = setInterval(fetchData, 5 * 1000);

        // Cleanup interval on component unmount
        return () => clearInterval(intervalId);
    }, []);

    return (
        <div className="list">
        </div>
    );
};

export default LightDetails;

