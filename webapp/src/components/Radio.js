import React, { useState, useEffect } from 'react';
import LightDetails from "./LightDetails";

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

        <div className="card border-light mb-3" style={{maxWidth: '30rem'}}>
            <div className="card-header">Radio</div>
            {radio.is_alive &&
                <div className="card-body">
                    <h5 class="card-title">{radio.station_name}</h5>
                    {radio.playinfo &&
                        <h6 className="card-subtitle text-muted">{radio.playinfo}</h6>
                    }
                </div>
            }
        </div>

    );
};

export default Radio;

