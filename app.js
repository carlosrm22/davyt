const express = require('express');
const ytdl = require('ytdl-core');
const ffmpeg = require('fluent-ffmpeg');
const fs = require('fs');
const { Configuration, OpenAIApi } = require('openai');

const app = express();
const port = 3000;

// Configura tu API Key de OpenAI
const configuration = new Configuration({
    apiKey: 'TU_API_KEY',
});
const openai = new OpenAIApi(configuration);

app.use(express.json());
app.use(express.urlencoded({ extended: true }));

app.post('/download', async (req, res) => {
    const { url, option } = req.body;

    if (!ytdl.validateURL(url)) {
        return res.status(400).send('URL de YouTube no válida');
    }

    if (option === 'video') {
        ytdl(url, { format: 'mp4' }).pipe(res);
    } else if (option === 'audio') {
        const audioStream = ytdl(url, { filter: 'audioonly' });
        ffmpeg(audioStream)
            .format('mp3')
            .pipe(res);
    } else if (option === 'transcript') {
        const audioPath = './temp_audio.mp3';
        const audioStream = ytdl(url, { filter: 'audioonly' });
        ffmpeg(audioStream)
            .format('mp3')
            .save(audioPath)
            .on('end', async () => {
                const transcript = await openai.createTranscription(fs.createReadStream(audioPath), 'whisper-1');
                fs.unlinkSync(audioPath);
                res.send(transcript.data.text);
            });
    }
});

app.listen(port, () => {
    console.log(`Servidor escuchando en http://localhost:${port}`);
});
