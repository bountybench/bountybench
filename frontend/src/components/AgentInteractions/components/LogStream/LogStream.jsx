import { useEffect, useState, useRef } from "react";
import './LogStream.css';

const LogStream = () => {
    const [logs, setLogs] = useState([]);
    const logEndRef = useRef(null); // Create a ref for the end of the log container

    useEffect(() => {
        const eventSource = new EventSource("http://localhost:8000/logs/stream");

        eventSource.onmessage = (event) => {
            setLogs((prevLogs) => [...prevLogs, event.data]);
        };

        return () => {
            eventSource.close();
        };
    }, []);

    useEffect(() => {
        logEndRef.current?.scrollIntoView({ behavior: "smooth" }); // Scroll to the bottom whenever logs updates
    }, [logs]);

    if (!logs || logs.length === 0) {
        return <></>;
    }
    return (
        <div>
            <div className="log-content" style={{ whiteSpace: "pre-wrap", fontFamily: "monospace" }}>
                {logs.map((log, index) => (
                    <div className="log-text" key={index}>{log}</div>
                ))}
                <div ref={logEndRef} /> {/* Empty div to scroll into view */}
            </div>
        </div>
    );
};

export default LogStream;