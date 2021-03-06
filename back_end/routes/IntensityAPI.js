var express = require("express");
var router = express.Router();
//const { spawn } = require("child_process");
//Path to the JSON file when created
const jsonFilePath = "./Tracker/Output.json";
const fs = require("fs");

//This method reads the file
const readFile = (
  callback,
  returnJson = false,
  filePath = jsonFilePath,
  encoding = "utf8"
) => {
  fs.readFile(filePath, encoding, (err, data) => {
    if (err) {
      throw err;
    }

    callback(returnJson ? JSON.parse(data) : data);
  });
};

//Sends the JSON data,Parses this data and Displays
router.get("/", function(req, res) {
  fs.readFile(jsonFilePath, "utf8", (err, data) => {
    if (err) {
      throw err;
    }

    res.send(JSON.parse(data));
  });
});

// // CREATE
// router.post("/framenumber", (req, res) => {
//   readFile(data => {
//     const framenumber = Object.keys(data).length + 1;
//   }, true);
// });

module.exports = router;
