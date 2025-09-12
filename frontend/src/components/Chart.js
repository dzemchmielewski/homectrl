import React, { useState, useEffect, forwardRef } from 'react';
import {useExpandable} from "../ExpandableContext";

const Chart = forwardRef(({chartData, facet}, ref) => {
    const [img, setImg] = useState([]);
    const { isExpanded, toggle } = useExpandable();

    useEffect(() => {
        const fetchData = async () => {
            try {
                if (chartData.model !== undefined) {
                    const response = await fetch(process.env.REACT_APP_HOMECTRL_RESTAPI_URL + '/chart/hours24/' + chartData.model + '/' + chartData.name);
                    const imageBlob = await response.blob();
                    const imageObjectURL = URL.createObjectURL(imageBlob);
                    setImg(imageObjectURL);
                }
            } catch (error) {
                console.error('Error fetching data:', error);
            }
        };

        // Initial fetch
        fetchData();

        const intervalId = setInterval(fetchData, 1 * 60 * 1000);

        // Cleanup interval on component unmount
        return () => clearInterval(intervalId);
    }, [chartData]);

    if (chartData.model === undefined) {
        return null;
    }
    return (
        <div className="card border-light mb-3" style={{maxWidth: '30rem'}} ref={ref}>
            <div
                className="card-header"
                style={{ cursor: 'pointer' }}
                onClick={() => toggle(facet)}>
                {chartData.label} {chartData.name} - last 24h
            </div>
            {isExpanded(facet) && (
            <div className="card-body">
                <p className="card-text">
                    <img src={img} alt="Some graph" className="img-fluid"/>
                </p>
            </div>
            )}
            {isExpanded(facet) && (
            <p className="d-flex flex-row align-items-center">
                <div style={{margin: "auto"}}>
                    <div className="btn-group" role="group" aria-label="Basic radio toggle button group">
                        <input type="radio" className="btn-check" name="btnradio" id="btnradio1" autoComplete="off" checked=""/>
                        <label className="btn btn-outline-secondary" htmlFor="btnradio1">Radio 1</label>
                        <input type="radio" className="btn-check" name="btnradio" id="btnradio2" autoComplete="off" checked="true"/>
                        <label className="btn btn-outline-secondary" htmlFor="btnradio2">Radio 2</label>
                        <input type="radio" className="btn-check" name="btnradio" id="btnradio3" autoComplete="off" checked=""/>
                        <label className="btn btn-outline-secondary" htmlFor="btnradio3">Radio 3</label>
                    </div>
                </div>
            </p>
            )}
        </div>
    );
});

export default Chart;

