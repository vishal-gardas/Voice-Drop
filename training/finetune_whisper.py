"""
finetune_whisper.py - Fine-Tuning OpenAI Whisper with PEFT / LoRA for Speech & Language Processing (SLP).

This script fine-tunes `openai/whisper-tiny` (or `whisper-small`) on Indian English / Telephony speech
using Parameter-Efficient Fine-Tuning (LoRA) and computes Word Error Rate (WER) metrics.

Key SLP Concepts Demonstrated:
1. Acoustic Feature Extraction: 80-channel Log-Mel Filterbank computation.
2. Language Representation: Byte-Pair Encoding (BPE) subword tokenization.
3. Sequence-to-Sequence Modeling: Encoder-Decoder Transformer with Cross-Attention.
4. Parameter-Efficient Transfer Learning: Low-Rank Adaptation (LoRA) on attention projection matrices.
5. Quantitative Evaluation: Word Error Rate (WER) with normalized text transcripts.

Usage:
    python finetune_whisper.py --model_name openai/whisper-tiny --dataset_name google/fleurs --language en_in --num_epochs 3
"""

import os
import argparse
import torch
import evaluate
import numpy as np
from dataclasses import dataclass
from typing import Any, Dict, List, Union
from datasets import load_dataset, Audio
from transformers import (
    WhisperFeatureExtractor,
    WhisperTokenizer,
    WhisperProcessor,
    WhisperForConditionalGeneration,
    Seq2SeqTrainingArguments,
    Seq2SeqTrainer,
)
from peft import LoraConfig, get_peft_model


# ==============================================================================
# 1. Data Collator for Speech Seq2Seq Modeling
# ==============================================================================

@dataclass
class DataCollatorSpeechSeq2SeqWithPadding:
    """
    Collator to pad acoustic feature matrices (input_features) and target token sequences (labels).
    Labels with value -100 are ignored in the Cross-Entropy loss computation.
    """
    processor: Any

    def __call__(self, features: List[Dict[str, Union[List[int], torch.Tensor]]]) -> Dict[str, torch.Tensor]:
        # Extract and pad acoustic features (80 log-mel filterbanks x time_steps)
        input_features = [{"input_features": feature["input_features"]} for feature in features]
        batch = self.processor.feature_extractor.pad(input_features, return_tensors="pt")

        # Extract and pad target token labels
        label_features = [{"input_ids": feature["labels"]} for feature in features]
        labels_batch = self.processor.tokenizer.pad(label_features, return_tensors="pt")

        # Mask padding tokens so loss is not computed on padded positions
        labels = labels_batch["input_ids"].masked_fill(labels_batch.attention_mask.ne(1), -100)

        # If decoder_start_token_id is present at the start of the sequence, strip it
        if (labels[:, 0] == self.processor.tokenizer.bos_token_id).all().cpu().item():
            labels = labels[:, 1:]

        batch["labels"] = labels
        return batch


# ==============================================================================
# 2. Main Training & Evaluation Pipeline
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description="Fine-tune Whisper on Speech Dataset with LoRA")
    parser.add_argument("--model_name", type=str, default="openai/whisper-tiny", help="Base Whisper checkpoint")
    parser.add_argument("--dataset_name", type=str, default="google/fleurs", help="Hugging Face dataset identifier")
    parser.add_argument("--language", type=str, default="en_in", help="Language subset code (e.g., en_in or hi_in)")
    parser.add_argument("--output_dir", type=str, default="./whisper_lora_model", help="Directory to save checkpoint")
    parser.add_argument("--num_epochs", type=int, default=3, help="Number of training epochs")
    parser.add_argument("--batch_size", type=int, default=8, help="Per-device train batch size")
    parser.add_argument("--learning_rate", type=float, default=1e-3, help="LoRA learning rate")
    args = parser.parse_args()

    print("=" * 70)
    print(f"🎙️ [SLP LAB] Fine-Tuning {args.model_name} on {args.dataset_name} ({args.language})")
    print("=" * 70)

    # 1. Load Feature Extractor & Tokenizer
    print("\n[Step 1/6] Loading Feature Extractor (Log-Mel) & Tokenizer (BPE)...")
    feature_extractor = WhisperFeatureExtractor.from_pretrained(args.model_name)
    tokenizer = WhisperTokenizer.from_pretrained(args.model_name, language="English", task="transcribe")
    processor = WhisperProcessor.from_pretrained(args.model_name, language="English", task="transcribe")

    # 2. Load and Prepare Speech Dataset
    print(f"\n[Step 2/6] Loading dataset '{args.dataset_name}' [{args.language}]...")
    try:
        raw_dataset = load_dataset(args.dataset_name, args.language, trust_remote_code=True)
    except Exception as e:
        print(f"⚠️ Could not load {args.dataset_name}/{args.language} directly: {e}")
        print("Falling back to common_voice or small split...")
        raw_dataset = load_dataset("google/fleurs", "en_in", split="train[:500]").train_test_split(test_size=0.2)

    # Ensure audio is resampled to 16,000 Hz
    raw_dataset = raw_dataset.cast_column("audio", Audio(sampling_rate=16000))

    # Preprocessing function: Waveform -> 80-channel Log-Mel Spectrogram -> Token IDs
    def prepare_dataset(batch):
        audio = batch["audio"]
        # Extract Log-Mel filterbank features
        batch["input_features"] = feature_extractor(
            audio["array"],
            sampling_rate=audio["sampling_rate"]
        ).input_features[0]

        # Encode target transcription text into subword token IDs
        transcript = batch.get("transcription") or batch.get("sentence") or batch.get("raw_transcription") or ""
        batch["labels"] = tokenizer(transcript).input_ids
        return batch

    print("\n[Step 3/6] Preprocessing audio waveforms to 80-channel Log-Mel spectrograms...")
    train_split = raw_dataset["train"].select(range(min(len(raw_dataset["train"]), 1000)))
    val_split = (raw_dataset.get("validation") or raw_dataset.get("test"))
    if val_split:
        val_split = val_split.select(range(min(len(val_split), 200)))
    else:
        split_data = train_split.train_test_split(test_size=0.15)
        train_split, val_split = split_data["train"], split_data["test"]

    vectorized_train = train_split.map(prepare_dataset, remove_columns=train_split.column_names, num_proc=1)
    vectorized_val = val_split.map(prepare_dataset, remove_columns=val_split.column_names, num_proc=1)

    # 3. Load Pre-trained Base Model
    print(f"\n[Step 4/6] Loading base model '{args.model_name}' with frozen backbone...")
    model = WhisperForConditionalGeneration.from_pretrained(
        args.model_name,
        device_map="auto" if torch.cuda.is_available() else None
    )

    model.config.forced_decoder_ids = None
    model.config.suppress_tokens = []
    model.config.use_cache = False
    if hasattr(model, "generation_config"):
        model.generation_config.language = "english"
        model.generation_config.task = "transcribe"
        model.generation_config.forced_decoder_ids = None

    # 4. Configure Parameter-Efficient Fine-Tuning (PEFT / LoRA)
    print("\n[Step 5/6] Applying Low-Rank Adaptation (LoRA) to Multi-Head Attention layers...")
    peft_config = LoraConfig(
        r=16,                         # Rank of LoRA update matrices
        lora_alpha=32,                # Scaling parameter
        target_modules=["q_proj", "v_proj"], # Apply to Query and Value projections
        lora_dropout=0.05,
        bias="none",
        task_type="SEQ_2_SEQ_LM"
    )

    # 1. FIX: Dummy method for Transformers 4.46+
    def _dummy_kwargs(self, *args, **kwargs):
        return kwargs.get("model_kwargs", kwargs)
    setattr(WhisperForConditionalGeneration, "_prepare_encoder_decoder_kwargs_for_generation", _dummy_kwargs)
    import peft
    try:
        setattr(peft.tuners.lora.model.LoraModel, "_prepare_encoder_decoder_kwargs_for_generation", _dummy_kwargs)
    except AttributeError:
        pass

    # 2. FIX: Protect forward AND generate from unexpected kwargs pushed by PEFT/Trainer
    if getattr(WhisperForConditionalGeneration, "_is_patched", False) is False:
        # Protect forward()
        _orig_whisper_forward = WhisperForConditionalGeneration.forward
        def _whisper_safe_forward(self, *args, **kwargs):
            kwargs.pop("input_ids", None)
            kwargs.pop("inputs_embeds", None)
            return _orig_whisper_forward(self, *args, **kwargs)
        WhisperForConditionalGeneration.forward = _whisper_safe_forward

        # Protect generate()
        _orig_whisper_generate = WhisperForConditionalGeneration.generate
        def _whisper_safe_generate(self, *args, **kwargs):
            kwargs.pop("labels", None)
            return _orig_whisper_generate(self, *args, **kwargs)
        WhisperForConditionalGeneration.generate = _whisper_safe_generate

        WhisperForConditionalGeneration._is_patched = True

    # 3. Use get_peft_model (compatible with all current PEFT versions).
    model = get_peft_model(model, peft_config)
    model.print_trainable_parameters()


    # 5. Define Metric Computation (Word Error Rate - WER)
    metric = evaluate.load("wer")

    def compute_metrics(pred):
        pred_ids = pred.predictions
        label_ids = pred.label_ids

        if isinstance(pred_ids, tuple):
            pred_ids = pred_ids[0]
        if hasattr(pred_ids, "ndim") and pred_ids.ndim == 3:
            pred_ids = np.argmax(pred_ids, axis=-1)

        # Replace -100 with pad_token_id
        label_ids[label_ids == -100] = tokenizer.pad_token_id

        pred_str = tokenizer.batch_decode(pred_ids, skip_special_tokens=True)
        label_str = tokenizer.batch_decode(label_ids, skip_special_tokens=True)

        wer_score = 100 * metric.compute(predictions=pred_str, references=label_str)
        return {"wer": round(wer_score, 2)}

    data_collator = DataCollatorSpeechSeq2SeqWithPadding(processor=processor)

    # 6. Training Arguments & Trainer Setup
    try:
        # Transformers >= 4.44
        training_args = Seq2SeqTrainingArguments(
            output_dir=args.output_dir,
            per_device_train_batch_size=args.batch_size,
            gradient_accumulation_steps=2,
            learning_rate=args.learning_rate,
            warmup_steps=50,
            num_train_epochs=args.num_epochs,
            eval_strategy="epoch",
            save_strategy="epoch",
            predict_with_generate=True,
            fp16=torch.cuda.is_available(),
            per_device_eval_batch_size=args.batch_size,
            generation_max_length=128,
            logging_steps=25,
            remove_unused_columns=False,
            label_names=["labels"],
            load_best_model_at_end=True,
            metric_for_best_model="wer",
            greater_is_better=False,
            report_to=["none"]
        )
    except Exception:
        # Transformers < 4.44
        training_args = Seq2SeqTrainingArguments(
            output_dir=args.output_dir,
            per_device_train_batch_size=args.batch_size,
            gradient_accumulation_steps=2,
            learning_rate=args.learning_rate,
            warmup_steps=50,
            num_train_epochs=args.num_epochs,
            evaluation_strategy="epoch",
            save_strategy="epoch",
            predict_with_generate=True,
            fp16=torch.cuda.is_available(),
            per_device_eval_batch_size=args.batch_size,
            generation_max_length=128,
            logging_steps=25,
            remove_unused_columns=False,
            label_names=["labels"],
            load_best_model_at_end=True,
            metric_for_best_model="wer",
            greater_is_better=False,
            report_to=["none"]
        )

    trainer = Seq2SeqTrainer(
        args=training_args,
        model=model,
        train_dataset=vectorized_train,
        eval_dataset=vectorized_val,
        data_collator=data_collator,
        compute_metrics=compute_metrics,
        tokenizer=processor.feature_extractor,
    )

    print("\n[Step 6/6] Starting LoRA Fine-Tuning...")
    trainer.train()

    print("\n Evaluating final fine-tuned model...")
    eval_results = trainer.evaluate()
    print(f" Final Evaluation WER: {eval_results.get('eval_wer', 'N/A')}%")

    # Save fine-tuned adapter weights
    print(f"\n Saving LoRA adapter checkpoint to {args.output_dir}...")
    model.save_pretrained(args.output_dir)
    processor.save_pretrained(args.output_dir)
    print(" Training completed successfully! Model is ready for deployment in VoiceDrop-2.0.")


if __name__ == "__main__":
    main()
