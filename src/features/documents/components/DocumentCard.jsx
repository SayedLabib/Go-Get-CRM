import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/apiClient';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import {
  Eye,
  Trash2,
  CheckCircle
} from 'lucide-react';
import { toast } from 'sonner';

const STATUS_OPTIONS = ['Pending Review', 'Reviewed', 'Processed', 'Archived'];

const statusColors = {
  'Pending Review': 'text-yellow-dark border-yellow/20 bg-yellow/10',
  'Reviewed': 'text-blue-700 border-blue-500/20 bg-blue-500/10',
  'Processed': 'text-green-700 border-green-500/20 bg-green-500/10',
  'Archived': 'text-gray-700 border-gray-500/20 bg-gray-500/10'
};

// Category is the Document Types master list's real, admin-editable
// taxonomy (src/pages/DocumentTypes.jsx). This substring map only covers
// legacy/imported document_type strings that don't match any current
// master-list entry.
const categoryIcons = {
  'Tax Slip': '📄',
  'Receipt': '🧾',
  'Bank Statement': '🏦',
  'Invoice': '📋',
  'Financial Statement': '💰',
  'Corporate Document': '🏢',
  'ID Document': '🪪',
  'Other': '📎'
};

export default function DocumentCard({ document: doc, clientName, onView, onDelete }) {
  const queryClient = useQueryClient();
  const { data: documentTypes = [] } = useQuery({
    queryKey: ['documentTypes'],
    queryFn: () => api.entities.DocumentType.list(),
  });

  const statusMutation = useMutation({
    mutationFn: (status) => api.entities.Document.update(doc.id, { status }),
    onSuccess: () => {
      // Documents lists are fetched under a few different scoped keys
      // across the app (['documents'], ['documents', clientId]) — matching
      // on the shared prefix refreshes whichever list this card is in.
      queryClient.invalidateQueries({ predicate: (query) => query.queryKey[0] === 'documents' });
      toast.success('Document status updated');
    },
    onError: (error) => toast.error(error.message || 'Failed to update status'),
  });
  const categoryByName = documentTypes.reduce((map, dt) => {
    map[dt.name] = dt.category || 'Other';
    return map;
  }, {});

  const getTypeIcon = (docType) => {
    const category = categoryByName[docType];
    if (category && categoryIcons[category]) return categoryIcons[category];
    for (const [key, icon] of Object.entries(categoryIcons)) {
      if (docType.includes(key)) return icon;
    }
    return categoryIcons.Other;
  };

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  return (
    <Card className="border-none shadow-sm hover:shadow-md transition-all">
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-3">
          {/* Icon & Info */}
          <div className="flex items-start gap-3 flex-1 min-w-0">
            <div className="text-3xl flex-shrink-0">
              {getTypeIcon(doc.document_type)}
            </div>
            <div className="flex-1 min-w-0">
              <h4 className="font-semibold text-navy truncate mb-1">
                {doc.document_name}
              </h4>
              <p className="text-xs text-muted-foreground mb-2">
                {doc.document_type}
              </p>

              {/* Metadata */}
              <div className="flex flex-wrap gap-2 text-xs text-muted-foreground mb-2">
                {doc.file_size && (
                  <span>{formatFileSize(doc.file_size)}</span>
                )}
                {doc.tax_year && (
                  <span>• {doc.tax_year}</span>
                )}
                {doc.created_date && (
                  <span>• {formatDate(doc.created_date)}</span>
                )}
              </div>

              {/* Tags & Folder */}
              <div className="flex flex-wrap gap-1">
                {doc.folder && (
                  <Badge variant="secondary" className="text-xs bg-navy/5 text-navy">
                    📁 {doc.folder}
                  </Badge>
                )}
                {doc.is_verified && (
                  <Badge variant="secondary" className="text-xs bg-green-500/10 text-green-700">
                    <CheckCircle className="w-3 h-3 mr-1" />
                    Verified
                  </Badge>
                )}
              </div>
            </div>
          </div>

          {/* Status — one-click change, no separate edit mode */}
          <Select value={doc.status} onValueChange={(status) => statusMutation.mutate(status)}>
            <SelectTrigger
              className={`${statusColors[doc.status] || ''} border h-7 w-auto text-xs font-medium flex-shrink-0 px-2 gap-1`}
            >
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-white">
              {STATUS_OPTIONS.map((status) => (
                <SelectItem key={status} value={status} className="text-slate-900 text-xs">
                  {status}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Description */}
        {doc.description && (
          <p className="text-sm text-muted-foreground mt-3 pt-3 border-t">
            {doc.description}
          </p>
        )}

        {/* Actions */}
        <div className="flex gap-2 mt-3 pt-3 border-t">
          <Button
            size="sm"
            variant="outline"
            onClick={() => onView?.(doc)}
            className="flex-1 gap-1"
          >
            <Eye className="w-3 h-3" />
            Preview
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => onDelete(doc)}
            className="text-red border-red hover:bg-red hover:text-white"
          >
            <Trash2 className="w-3 h-3" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}