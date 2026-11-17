import { useEffect } from 'react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { useModels } from '@/hooks/useModels';
import { useSelectedModel } from '@/hooks/useSelectedModel';
import { Cpu } from 'lucide-react';

export const ModelPicker = () => {
  const { models, isLoading } = useModels();
  const { model: selectedModel, setModel } = useSelectedModel();

  const defaultModel =
    models.find((m) => m.is_default) ||
    models.find((m) => m.is_finetuned) ||
    models.find((m) => m.name.includes('llama')) ||
    models[0];
  const known = models.some((m) => m.name === selectedModel);
  const selectValue = (known && selectedModel) || defaultModel?.name || '';
  const disabled = isLoading || models.length === 0;
  const placeholder = isLoading
    ? 'Loading models...'
    : models.length === 0
      ? 'No models available'
      : 'Select model';

  // Pick a model once the list loads, or when the saved choice is no longer offered.
  useEffect(() => {
    if (models.length > 0 && !known && defaultModel) {
      setModel(defaultModel.name);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [models, known]);

  return (
    <div className="flex items-center gap-2">
      <Cpu className="w-4 h-4 text-slate-200" />
      <Select value={selectValue} onValueChange={setModel} disabled={disabled}>
        <SelectTrigger className="w-[240px] bg-slate-800 border-slate-600 text-slate-100 hover:bg-slate-700 data-[placeholder]:text-slate-300">
          <SelectValue placeholder={placeholder} />
        </SelectTrigger>
        <SelectContent className="bg-slate-800 text-slate-100 border-slate-600">
          {models.map((model) => (
            <SelectItem
              key={model.name}
              value={model.name}
              className="text-slate-100 data-[highlighted]:bg-slate-700 data-[highlighted]:text-white"
            >
              <div className="flex min-w-0 items-center justify-between gap-2">
                <span className="min-w-0 truncate">{model.name}</span>
                {model.is_finetuned && (
                  <Badge className="h-4 shrink-0 whitespace-nowrap px-1.5 text-[10px] bg-violet-600 hover:bg-violet-600">fine-tuned</Badge>
                )}
                {model.name === defaultModel?.name && !model.is_finetuned && (
                  <Badge variant="secondary" className="h-4 shrink-0 whitespace-nowrap text-[10px]">
                    default
                  </Badge>
                )}
              </div>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
};
