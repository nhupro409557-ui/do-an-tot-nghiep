import React, { useState } from 'react';
import { updateUserProfile } from '../../../services/authDb';
import type { AccountAddress } from '../types/accountDashboardTypes';
import { emptyAddress, getMapSearchAddress, getNewAddressLine } from '../utils/accountAddressUtils';

type UseAccountAddressesParams = {
  userId?: string;
  addresses: AccountAddress[];
};

export function useAccountAddresses({ userId, addresses }: UseAccountAddressesParams) {
  const [addressDraft, setAddressDraft] = useState(emptyAddress);
  const [isAddressFormOpen, setIsAddressFormOpen] = useState(false);
  const [editingAddressId, setEditingAddressId] = useState<string | null>(null);

  const mapPredictionAddress = getMapSearchAddress(addressDraft.addressData, addressDraft.addressLine);

  const updateAddresses = (nextAddresses: AccountAddress[]) => {
    if (!userId) return;
    updateUserProfile(userId, { addresses: nextAddresses });
  };

  const handleAddAddress = (event: React.FormEvent) => {
    event.preventDefault();
    if (!userId) return;

    const fullAddressLine = getNewAddressLine(addressDraft.addressData, addressDraft.addressLine);

    if (editingAddressId) {
      updateUserProfile(userId, {
        addresses: addresses.map(address => address.id === editingAddressId ? {
          ...address,
          receiverName: addressDraft.receiverName.trim(),
          receiverPhone: addressDraft.receiverPhone.trim(),
          addressLine: fullAddressLine,
          addressData: addressDraft.addressData,
          mapQueryAddress: mapPredictionAddress,
          lat: addressDraft.lat,
          lng: addressDraft.lng,
          mapUrl: addressDraft.mapUrl,
          note: addressDraft.note.trim(),
          isMapVerified: Boolean(addressDraft.mapUrl),
        } : address),
      });
    } else {
      const nextAddress: AccountAddress = {
        id: crypto.randomUUID(),
        receiverName: addressDraft.receiverName.trim(),
        receiverPhone: addressDraft.receiverPhone.trim(),
        addressLine: fullAddressLine,
        addressData: addressDraft.addressData,
        mapQueryAddress: mapPredictionAddress,
        lat: addressDraft.lat,
        lng: addressDraft.lng,
        mapUrl: addressDraft.mapUrl,
        note: addressDraft.note.trim(),
        isDefault: addresses.length === 0,
        isMapVerified: Boolean(addressDraft.mapUrl),
      };

      updateUserProfile(userId, { addresses: [...addresses, nextAddress] });
    }

    setAddressDraft(emptyAddress);
    setEditingAddressId(null);
    setIsAddressFormOpen(false);
  };

  const openNewAddressForm = () => {
    setAddressDraft(emptyAddress);
    setEditingAddressId(null);
    setIsAddressFormOpen(true);
  };

  const openEditAddressForm = (address: AccountAddress) => {
    setAddressDraft({
      receiverName: address.receiverName,
      receiverPhone: address.receiverPhone,
      addressLine: address.addressLine,
      addressData: address.addressData || {
        provinceId: '',
        provinceName: '',
        districtId: '',
        districtName: '',
        wardId: '',
        wardName: '',
        street: address.addressLine,
      },
      mapQueryAddress: address.mapQueryAddress || '',
      lat: address.lat,
      lng: address.lng,
      mapUrl: address.mapUrl || '',
      note: address.note || '',
    });
    setEditingAddressId(address.id);
    setIsAddressFormOpen(true);
  };

  const verifyAddressOnMap = (address: AccountAddress) => {
    const mapUrl = address.mapUrl || `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(address.addressLine)}`;
    window.open(mapUrl, '_blank');
    updateAddresses(addresses.map(item => item.id === address.id ? { ...item, mapUrl, isMapVerified: true } : item));
  };

  return {
    addressDraft,
    editingAddressId,
    emptyAddress,
    handleAddAddress,
    isAddressFormOpen,
    mapPredictionAddress,
    openEditAddressForm,
    openNewAddressForm,
    setAddressDraft,
    setEditingAddressId,
    setIsAddressFormOpen,
    updateAddresses,
    verifyAddressOnMap,
  };
}
