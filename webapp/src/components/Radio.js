import React, { useState, useEffect } from 'react';

const Radio = () => {
    const [radio, setRadio] = useState([]);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const response = await fetch(process.env.REACT_APP_HOMECTRL_RESTAPI_URL + '/radio');
                const data = await response.json();
                setRadio(data.result);
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
            <h2>Radio</h2>
            {radio.is_alive &&
                <div>
                    <h3>{radio.station_name}</h3>
                    {radio.playinfo &&
                        <h4>{radio.playinfo}</h4>
                    }
                </div>
            }
        </div>
    );
};

export default Radio;

