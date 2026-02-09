const express = require("express");
const app = express();

// Parse JSON request bodies
app.use(express.json());

app.post("/logs", (req, res) => {
    console.log(JSON.stringify(req.body, null, 2));
    res.status(200).send();
});

app.listen(9000, () => {
    console.log("Server is running on port 9000");
});