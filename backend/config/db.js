const mongoose = require("mongoose");

const connectDB = async () => {
  try {
    await mongoose.connect(process.env.MONGO_URI, {
      serverSelectionTimeoutMS: 5000,
    });
    console.log("MongoDB Connected...");
  } catch (err) {
    console.error("⚠️ MongoDB connection error:", err.message);
    console.log(
      "⚠️ Running server in standalone mode without active DB connection.",
    );
  }
};

module.exports = connectDB;
