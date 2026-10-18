"""Voice pipeline order for Pipecat; used by pipecat_livekit_bot.py --voice.

Supply configured processors; the Pipecat runner owns the connection and
shutdown lifecycle.
"""


def build_pipeline(transport, stt, llm, tts, context_aggregator):
    from pipecat.pipeline.pipeline import Pipeline

    return Pipeline([
        transport.input(),
        stt,
        context_aggregator.user(),
        llm,
        tts,
        transport.output(),
        context_aggregator.assistant(),
    ])
