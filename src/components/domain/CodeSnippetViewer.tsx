import React from 'react';
import { FileCode, Tag } from 'lucide-react';
import { Badge } from '@/components/common/Badge';

export interface CodeSnippetViewerProps {
  filePath: string;
  lineNumber: number;
  snippet: string;
  astNodeType?: string;
  isDeadCode?: boolean;
  referenceType?: string;
}

export const CodeSnippetViewer: React.FC<CodeSnippetViewerProps> = ({
  filePath,
  lineNumber,
  snippet,
  astNodeType,
  isDeadCode,
  referenceType,
}) => {
  const lines = snippet.split('\n');

  return (
    <div className="rounded-lg border border-border bg-[#0b0f19] overflow-hidden">
      {/* File Header */}
      <div className="px-3.5 py-2 bg-surface-100/80 border-b border-border flex items-center justify-between text-xs">
        <div className="flex items-center gap-2 text-zinc-300 font-mono">
          <FileCode className="w-3.5 h-3.5 text-indigo-400" />
          <span>{filePath}</span>
          <span className="text-zinc-500">:L{lineNumber}</span>
        </div>
        <div className="flex items-center gap-1.5">
          {referenceType && (
            <Badge variant="zinc" size="sm" className="font-mono text-[10px]">
              {referenceType}
            </Badge>
          )}
          {astNodeType && (
            <Badge variant="violet" size="sm" className="font-mono text-[10px]">
              <Tag className="w-2.5 h-2.5 mr-1" />
              {astNodeType}
            </Badge>
          )}
          {isDeadCode && (
            <Badge variant="rose" size="sm" className="font-mono text-[10px]">
              Dead Code Candidate
            </Badge>
          )}
        </div>
      </div>

      {/* Code Body */}
      <div className="p-3 text-xs font-mono overflow-x-auto text-zinc-200 leading-relaxed">
        {lines.map((line, idx) => {
          const currentLineNum = lineNumber + idx;
          return (
            <div key={idx} className="flex hover:bg-surface-100/40 px-1 -mx-1 rounded">
              <span className="w-9 select-none text-zinc-600 text-right pr-3 shrink-0">
                {currentLineNum}
              </span>
              <pre className="font-mono whitespace-pre text-zinc-200">{line}</pre>
            </div>
          );
        })}
      </div>
    </div>
  );
};
