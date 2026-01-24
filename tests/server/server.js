const express = require("express");
const app = express();

// Parse JSON request bodies
app.use(express.json());

app.post("/logs", (req, res) => {
    console.log(req.body);
    res.status(200).send();
});

app.listen(3000, () => {
    console.log("Server is running on port 3000");
});