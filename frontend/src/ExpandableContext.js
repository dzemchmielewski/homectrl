import React, { createContext, useState, useContext } from 'react';

const ExpandableContext = createContext();

export const ExpandableProvider = ({ children }) => {
    const [expanded, setExpanded] = useState({});

    const toggle = (key) => {
        setExpanded(prev => ({ ...prev, [key]: !prev[key] }));
    };

    const isExpanded = (key) => !!expanded[key];

    return (
        <ExpandableContext.Provider value={{ isExpanded, toggle }}>
            {children}
        </ExpandableContext.Provider>
    );
};

export const useExpandable = () => useContext(ExpandableContext);
