.scroll-container {
    display: flex;
    overflow-x: auto;
    white-space: nowrap;
    padding: 10px;
    gap: 20px;
    background: #f8f9fa;
    border-radius: 15px;
    margin-bottom: 20px;
}
.flag-btn {
    display: inline-block;
    text-align: center;
    cursor: pointer;
    transition: transform 0.2s;
}
.flag-btn:hover {
    transform: scale(1.1);
}
.flag-btn img {
    width: 60px; /* حجم العلم */
    height: 40px;
    border-radius: 5px;
    object-fit: cover;
    box-shadow: 0 4px 8px rgba(0,0,0,0.2);
}
.flag-label {
    display: block;
    font-size: 12px;
    margin-top: 5px;
    color: #333;
    font-weight: bold;
}
